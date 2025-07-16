from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import asyncio
import json
import random
import uuid
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

app = FastAPI()

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class GameState(Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"

@dataclass
class Card:
    suit: str  # hearts, diamonds, clubs, spades
    rank: str  # A, 2-10, J, Q, K
    
    def get_value(self) -> int:
        """Get the point value of the card"""
        if self.rank == 'A':
            return 0
        elif self.rank in ['J', 'Q']:
            return 10 if self.rank == 'J' else 12
        elif self.rank == 'K':
            # Red kings are -5, black kings are 13
            return -5 if self.suit in ['hearts', 'diamonds'] else 13
        else:
            return int(self.rank)

@dataclass
class Player:
    id: str
    nickname: str
    cards: List[Card]
    visible_cards: List[bool]  # Which cards player can see
    websocket: Optional[WebSocket] = None
    
    def can_see_card(self, index: int) -> bool:
        return self.visible_cards[index] if index < len(self.visible_cards) else False

@dataclass
class GameRoom:
    id: str
    players: List[Player]
    deck: List[Card]
    discard_pile: List[Card]
    current_player_index: int
    state: GameState
    drawn_card: Optional[Card] = None
    round_count: int = 0
    band_called_by: Optional[str] = None
    game_results: Optional[dict] = None
    peeking_phase: bool = True
    players_peeked: List[str] = None
    
    def __post_init__(self):
        if self.players_peeked is None:
            self.players_peeked = []
    
    def get_total_score(self, player_id: str) -> int:
        """Calculate total score for a player"""
        player = next((p for p in self.players if p.id == player_id), None)
        if not player:
            return 0
        return sum(card.get_value() for card in player.cards)
    
    def can_call_band(self) -> bool:
        """Check if players can call Ban'd (not in first round)"""
        return self.round_count > 0
    
    def all_players_peeked(self) -> bool:
        """Check if all players have peeked at their initial cards"""
        return len(self.players_peeked) >= len(self.players)

# Global state
rooms: Dict[str, GameRoom] = {}
active_connections: Dict[str, WebSocket] = {}

def create_deck() -> List[Card]:
    """Create a standard 52-card deck"""
    suits = ['hearts', 'diamonds', 'clubs', 'spades']
    ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    deck = [Card(suit, rank) for suit in suits for rank in ranks]
    random.shuffle(deck)
    return deck

def deal_cards(deck: List[Card], num_players: int) -> List[List[Card]]:
    """Deal 4 cards to each player"""
    hands = [[] for _ in range(num_players)]
    for i in range(4):  # Each player gets 4 cards
        for j in range(num_players):
            if deck:
                hands[j].append(deck.pop())
    return hands

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/room/{room_id}", response_class=HTMLResponse)
async def room(request: Request, room_id: str):
    return templates.TemplateResponse("game.html", {"request": request, "room_id": room_id})

@app.websocket("/ws/{room_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, player_id: str):
    await websocket.accept()
    active_connections[player_id] = websocket
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await handle_message(room_id, player_id, message)
    except WebSocketDisconnect:
        if player_id in active_connections:
            del active_connections[player_id]
        await handle_player_disconnect(room_id, player_id)

async def handle_message(room_id: str, player_id: str, message: dict):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")
    
    if message_type == "join_room":
        await join_room(room_id, player_id, message.get("nickname"))
    elif message_type == "start_game":
        await start_game(room_id)
    elif message_type == "peek_cards":
        await peek_initial_cards(room_id, player_id)
    elif message_type == "draw_card":
        await draw_card(room_id, player_id, message.get("from_discard", False))
    elif message_type == "replace_card":
        await replace_card(room_id, player_id, message.get("hand_index"))
    elif message_type == "discard_drawn":
        await discard_drawn_card(room_id, player_id)
    elif message_type == "use_special":
        await use_special_card(room_id, player_id, message.get("action"), message.get("target"))
    elif message_type == "call_band":
        await call_band(room_id, player_id)
    elif message_type == "chat":
        await broadcast_chat(room_id, player_id, message.get("message"))

async def join_room(room_id: str, player_id: str, nickname: str):
    """Add player to room"""
    if room_id not in rooms:
        rooms[room_id] = GameRoom(
            id=room_id,
            players=[],
            deck=[],
            discard_pile=[],
            current_player_index=0,
            state=GameState.WAITING,
            peeking_phase=False,  # Don't start peeking until game starts
            players_peeked=[]
        )
    
    room = rooms[room_id]
    
    # Check if player already exists by nickname (not player_id)
    existing_player = next((p for p in room.players if p.nickname == nickname), None)
    if existing_player:
        # Update existing player with new connection info
        old_player_id = existing_player.id
        existing_player.id = player_id  # Update to new player_id
        existing_player.websocket = active_connections.get(player_id)
        
        # Update the players_peeked list if the old player_id was there
        if old_player_id in room.players_peeked:
            room.players_peeked.remove(old_player_id)
            if player_id not in room.players_peeked:
                room.players_peeked.append(player_id)
        
        # Send reconnection message to player
        websocket = active_connections.get(player_id)
        if websocket:
            reconnect_info = {
                "type": "reconnected",
                "message": f"Welcome back, {nickname}! You've been reconnected to the game."
            }
            try:
                await websocket.send_text(json.dumps(reconnect_info))
            except:
                pass
    else:
        # Check if room is full
        if len(room.players) >= 4:
            # Room is full, send error to player
            websocket = active_connections.get(player_id)
            if websocket:
                error_info = {
                    "type": "error",
                    "message": "Room is full! Maximum 4 players allowed."
                }
                try:
                    await websocket.send_text(json.dumps(error_info))
                except:
                    pass
                return
        
        # Add new player
        player = Player(
            id=player_id,
            nickname=nickname,
            cards=[],
            visible_cards=[False, False, False, False],  # Initialize with 4 positions
            websocket=active_connections.get(player_id)
        )
        room.players.append(player)
    
    await broadcast_room_state(room_id)

async def start_game(room_id: str):
    """Start the game if enough players"""
    if room_id not in rooms:
        return
        
    room = rooms[room_id]
    if len(room.players) < 2:
        return
    
    # Initialize game
    room.deck = create_deck()
    hands = deal_cards(room.deck, len(room.players))
    
    for i, player in enumerate(room.players):
        player.cards = hands[i]
        # All cards start hidden - players must peek to see their bottom 2 cards
        player.visible_cards = [False, False, False, False]
    
    # Place first card in discard pile
    if room.deck:
        room.discard_pile = [room.deck.pop()]
    
    # Random first player
    room.current_player_index = random.randint(0, len(room.players) - 1)
    
    # Now that cards are dealt, enter peeking phase
    room.peeking_phase = True
    room.players_peeked = []
    room.state = GameState.WAITING  # Keep waiting until all players peek
    
    await broadcast_room_state(room_id)

async def peek_initial_cards(room_id: str, player_id: str):
    """Allow player to peek at their bottom 2 cards at game start"""
    if room_id not in rooms:
        return
        
    room = rooms[room_id]
    player = next((p for p in room.players if p.id == player_id), None)
    
    if not player or not room.peeking_phase or player_id in room.players_peeked:
        return
    
    # Make sure visible_cards list is properly initialized
    if len(player.visible_cards) < 4:
        player.visible_cards = [False, False, False, False]
    
    # Make sure player has cards
    if len(player.cards) < 4:
        # Send error message to player
        if player.websocket:
            error_info = {
                "type": "error",
                "message": "Cards haven't been dealt yet. Please wait for the game to start."
            }
            try:
                await player.websocket.send_text(json.dumps(error_info))
            except:
                pass
        return
    
    # Temporarily show bottom 2 cards (positions 2 and 3) 
    player.visible_cards[2] = True
    player.visible_cards[3] = True
    
    # Mark this player as having peeked
    room.players_peeked.append(player_id)
    
    # Send the revealed cards to the player
    if player.websocket:
        peek_info = {
            "type": "cards_peeked",
            "cards": [
                asdict(player.cards[2]),
                asdict(player.cards[3])
            ],
            "message": "Remember these cards! They will be hidden again in 5 seconds."
        }
        try:
            await player.websocket.send_text(json.dumps(peek_info))
        except:
            pass
    
    # After a brief delay, hide the cards again
    await asyncio.sleep(5)  # 5 second peek
    player.visible_cards[2] = False
    player.visible_cards[3] = False
    
    # Check if all players have peeked
    if room.all_players_peeked():
        room.peeking_phase = False
        room.state = GameState.PLAYING
    
    await broadcast_room_state(room_id)

async def broadcast_room_state(room_id: str):
    """Broadcast current room state to all players"""
    if room_id not in rooms:
        return
        
    room = rooms[room_id]
    
    for player in room.players:
        if player.websocket:
            # Create player-specific state
            state = {
                "type": "game_state",
                "room_id": room_id,
                "state": room.state.value,
                "players": [
                    {
                        "id": p.id,
                        "nickname": p.nickname,
                        "card_count": len(p.cards),
                        "is_current": i == room.current_player_index
                    }
                    for i, p in enumerate(room.players)
                ],
                "your_cards": [
                    {
                        "suit": card.suit,
                        "rank": card.rank,
                        "visible": player.can_see_card(i)
                    }
                    for i, card in enumerate(player.cards)
                ],
                "discard_top": asdict(room.discard_pile[-1]) if room.discard_pile else None,
                "current_player": room.current_player_index,
                "is_your_turn": room.players[room.current_player_index].id == player.id if room.state == GameState.PLAYING else False,
                "drawn_card": asdict(room.drawn_card) if room.drawn_card else None,
                "drawn_card_is_special": room.drawn_card.rank in ['7', '8', '9'] if room.drawn_card else False,
                "round_count": room.round_count,
                "can_call_band": room.can_call_band(),
                "band_called_by": room.band_called_by,
                "game_results": room.game_results,
                "peeking_phase": room.peeking_phase,
                "has_peeked": player.id in room.players_peeked,
                "waiting_for_peeks": [p.nickname for p in room.players if p.id not in room.players_peeked] if room.peeking_phase else []
            }
            
            try:
                await player.websocket.send_text(json.dumps(state))
            except:
                pass

async def draw_card(room_id: str, player_id: str, from_discard: bool):
    """Handle card drawing"""
    if room_id not in rooms:
        return
        
    room = rooms[room_id]
    current_player = room.players[room.current_player_index]
    
    if current_player.id != player_id:
        return  # Not player's turn
    
    if room.drawn_card:
        return  # Already drew a card
    
    if from_discard and room.discard_pile:
        room.drawn_card = room.discard_pile.pop()
    elif room.deck:
        room.drawn_card = room.deck.pop()
    
    await broadcast_room_state(room_id)

async def replace_card(room_id: str, player_id: str, hand_index: int):
    """Replace a card in hand with drawn card"""
    if room_id not in rooms:
        return
        
    room = rooms[room_id]
    current_player = room.players[room.current_player_index]
    
    if current_player.id != player_id or not room.drawn_card:
        return
    
    if 0 <= hand_index < len(current_player.cards):
        # Replace card
        old_card = current_player.cards[hand_index]
        current_player.cards[hand_index] = room.drawn_card
        room.discard_pile.append(old_card)
        room.drawn_card = None
        
        # Next player's turn
        room.current_player_index = (room.current_player_index + 1) % len(room.players)
        
        # Increment round count after each complete turn
        if room.current_player_index == 0:
            room.round_count += 1
        
        await broadcast_room_state(room_id)

async def discard_drawn_card(room_id: str, player_id: str):
    """Discard the drawn card without replacing"""
    if room_id not in rooms:
        return
        
    room = rooms[room_id]
    current_player = room.players[room.current_player_index]
    
    if current_player.id != player_id or not room.drawn_card:
        return
    
    room.discard_pile.append(room.drawn_card)
    room.drawn_card = None
    
    # Next player's turn
    room.current_player_index = (room.current_player_index + 1) % len(room.players)
    
    # Increment round count after each complete turn
    if room.current_player_index == 0:
        room.round_count += 1
    
    await broadcast_room_state(room_id)

async def use_special_card(room_id: str, player_id: str, action: str, target: dict):
    """Handle special card actions (7, 8, 9) - only when drawn"""
    if room_id not in rooms:
        return
        
    room = rooms[room_id]
    player = next((p for p in room.players if p.id == player_id), None)
    
    if not player or not room.drawn_card or room.players[room.current_player_index].id != player_id:
        return
    
    # Check if drawn card has special power (only 7, 8, 9 can be used)
    card_rank = room.drawn_card.rank
    if card_rank not in ['7', '8', '9']:
        return
    
    if card_rank == '7' and action == 'view_own':
        # View one of your own cards (only hidden cards) - permanently revealed
        card_index = target.get('card_index')
        if (0 <= card_index < len(player.cards) and 
            not player.visible_cards[card_index]):
            
            # Permanently reveal this card
            player.visible_cards[card_index] = True
            
            # Send special message to player about revealed card
            if player.websocket:
                card_info = {
                    "type": "card_revealed",
                    "card": asdict(player.cards[card_index]),
                    "index": card_index,
                    "message": f"You used a 7 to reveal your card: {player.cards[card_index].rank} of {player.cards[card_index].suit}. This card will stay visible."
                }
                try:
                    await player.websocket.send_text(json.dumps(card_info))
                except:
                    pass
                    
    elif card_rank == '8' and action == 'view_other':
        # View another player's card
        target_player_id = target.get('player_id')
        card_index = target.get('card_index')
        target_player = next((p for p in room.players if p.id == target_player_id), None)
        
        if target_player and 0 <= card_index < len(target_player.cards):
            # Send card info to the viewing player
            if player.websocket:
                card_info = {
                    "type": "other_card_viewed",
                    "card": asdict(target_player.cards[card_index]),
                    "target_player": target_player.nickname,
                    "message": f"You used an 8 to view {target_player.nickname}'s card: {target_player.cards[card_index].rank} of {target_player.cards[card_index].suit}"
                }
                try:
                    await player.websocket.send_text(json.dumps(card_info))
                except:
                    pass
                    
    elif card_rank == '9' and action == 'swap_cards':
        # Swap any two cards on the table
        swap1 = target.get('swap1')  # {player_id, card_index}
        swap2 = target.get('swap2')  # {player_id, card_index}
        
        if swap1 and swap2:
            player1 = next((p for p in room.players if p.id == swap1['player_id']), None)
            player2 = next((p for p in room.players if p.id == swap2['player_id']), None)
            
            if (player1 and player2 and 
                0 <= swap1['card_index'] < len(player1.cards) and
                0 <= swap2['card_index'] < len(player2.cards)):
                
                # Perform the swap
                card1 = player1.cards[swap1['card_index']]
                card2 = player2.cards[swap2['card_index']]
                
                player1.cards[swap1['card_index']] = card2
                player2.cards[swap2['card_index']] = card1
                
                # Broadcast swap message
                swap_message = {
                    "type": "cards_swapped",
                    "message": f"{player.nickname} used a 9 to swap two cards on the table"
                }
                
                for p in room.players:
                    if p.websocket:
                        try:
                            await p.websocket.send_text(json.dumps(swap_message))
                        except:
                            pass
    
    # After using special power, discard the card and continue turn
    room.discard_pile.append(room.drawn_card)
    room.drawn_card = None
    room.current_player_index = (room.current_player_index + 1) % len(room.players)
    
    # Increment round count after each complete turn
    if room.current_player_index == 0:
        room.round_count += 1
    
    await broadcast_room_state(room_id)

async def call_band(room_id: str, player_id: str):
    """Handle when a player calls Ban'd"""
    if room_id not in rooms:
        return
        
    room = rooms[room_id]
    player = next((p for p in room.players if p.id == player_id), None)
    
    if not player or room.state != GameState.PLAYING:
        return
    
    # Check if Ban'd can be called (not in first round)
    if not room.can_call_band():
        return
    
    # Mark who called Ban'd and end the game
    room.band_called_by = player_id
    room.state = GameState.FINISHED
    
    # Calculate final scores for all players
    scores = []
    for p in room.players:
        # Reveal all cards
        p.visible_cards = [True, True, True, True]
        score = room.get_total_score(p.id)
        scores.append({
            'player_id': p.id,
            'nickname': p.nickname,
            'score': score,
            'cards': [asdict(card) for card in p.cards]
        })
    
    # Sort by score to find winner
    scores.sort(key=lambda x: x['score'])
    winner = scores[0]
    
    # Check if the person who called Ban'd has the lowest score
    caller_score = next((s for s in scores if s['player_id'] == player_id), None)
    if caller_score and caller_score['score'] == winner['score']:
        winner_message = f"{player.nickname} called Ban'd and won with {winner['score']} points!"
    else:
        winner_message = f"{player.nickname} called Ban'd but {winner['nickname']} won with {winner['score']} points!"
    
    room.game_results = {
        'caller': player.nickname,
        'winner': winner,
        'all_scores': scores,
        'message': winner_message
    }
    
    # Broadcast game end
    await broadcast_room_state(room_id)
    
    # Send game results to all players
    game_end_message = {
        "type": "game_ended",
        "results": room.game_results
    }
    
    for p in room.players:
        if p.websocket:
            try:
                await p.websocket.send_text(json.dumps(game_end_message))
            except:
                pass

async def broadcast_chat(room_id: str, player_id: str, message: str):
    """Broadcast chat message to all players in room"""
    if room_id not in rooms:
        return
        
    room = rooms[room_id]
    player = next((p for p in room.players if p.id == player_id), None)
    
    if not player:
        return
    
    chat_message = {
        "type": "chat",
        "player": player.nickname,
        "message": message
    }
    
    for p in room.players:
        if p.websocket:
            try:
                await p.websocket.send_text(json.dumps(chat_message))
            except:
                pass

async def handle_player_disconnect(room_id: str, player_id: str):
    """Handle player disconnection"""
    if room_id in rooms:
        room = rooms[room_id]
        player = next((p for p in room.players if p.id == player_id), None)
        if player:
            player.websocket = None
        await broadcast_room_state(room_id)

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 