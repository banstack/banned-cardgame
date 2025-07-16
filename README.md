# Ban'd - Online Card Game 🃏

An online multiplayer card game similar to Cabo, built with FastAPI, WebSockets, and HTMX for real-time gameplay.

## 🎮 Game Overview

Ban'd is a strategic card game where players try to achieve the lowest possible score by managing their hand of 4 cards. The game combines memory, strategy, and a bit of luck as players can only see some of their cards initially.

## 🎯 Game Rules

### Basic Setup
- 2-4 players per game
- Each player starts with 4 cards
- Players can initially see their bottom 2 cards only
- Goal: Get the lowest total score

### Card Values
- **Ace**: 0 points
- **Numbers 2-6**: Face value points
- **Numbers 7-9**: Face value + special powers
- **10, Jack**: 10 points
- **Queen**: 12 points
- **Red Kings** (Hearts/Diamonds): -5 points
- **Black Kings** (Clubs/Spades): 13 points

### Special Powers
- **7**: View one of your own hidden cards
- **8**: View another player's card
- **9**: Swap any two cards on the table (without viewing)

### Gameplay
1. Players take turns in clockwise order
2. On your turn, draw a card from either:
   - The deck (face down)
   - The discard pile (face up)
3. After drawing, you must either:
   - Replace one of your 4 cards with the drawn card
   - Discard the drawn card without replacing
4. If you draw a 7, 8, or 9, you can use its special power before deciding
5. After the first round, any player can call "Ban'd" to end the game
6. When "Ban'd" is called, all players reveal their cards
7. Lowest total score wins!

### Important Rules
- **Card Visibility**: You can only see your bottom 2 cards initially - remember them!
- **First Round Protection**: Cannot call "Ban'd" during the first round
- **Special Powers**: Use cards 7, 8, 9 strategically to gain advantages
- **No Take-Backs**: Once you've seen a card, you can't see it again (except with special powers)

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip

### Installation

1. **Clone or download the project files**

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the server**
   ```bash
   python main.py
   ```

4. **Open your browser**
   Navigate to `http://localhost:8000`

### Creating a Game

1. Enter your nickname
2. Click "Create Room" or enter a room code to join
3. Share the room code with friends
4. Start the game when 2+ players have joined

## 🎨 Features

### ✅ Implemented
- **Real-time multiplayer**: WebSocket-based gameplay
- **Room system**: Create and join game rooms with codes
- **Card management**: Draw, replace, and discard cards
- **Special card powers**: Cards 7, 8, 9 have unique abilities
- **Call Ban'd**: End game functionality (disabled in first round)
- **Game ending**: Score calculation and winner announcement
- **Card visibility**: Players can only see their initial 2 cards once
- **Live chat**: Communicate with other players
- **Responsive design**: Works on desktop and mobile
- **Modern UI**: Clean, card-game themed interface

### 🔄 Planned Enhancements
- Spectator mode
- Game replay system
- Sound effects
- Animations for card movements
- Multiple game rounds
- Tournament mode

## 🛠️ Technical Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTML, CSS, JavaScript with HTMX
- **Real-time**: WebSockets
- **Styling**: Modern CSS with gradients and animations

## 🎯 Project Structure

```
cabo/
├── main.py              # FastAPI server and game logic
├── requirements.txt     # Python dependencies
├── templates/
│   ├── index.html      # Landing page
│   └── game.html       # Game room interface
└── static/
    └── css/
        └── styles.css  # Game styling
```

## 🎮 How to Play (Step by Step)

1. **Join a Room**: Enter your nickname and create/join a room
2. **Wait for Players**: Game starts with 2+ players (max 4)
3. **Learn Your Cards**: Remember your bottom 2 visible cards
4. **Take Turns**: Draw → Replace/Discard → Next player
5. **Use Strategy**: 
   - Replace high-value cards with lower ones
   - Use special powers wisely
   - Remember other players' discarded cards
6. **Call "Ban'd"**: When you think you have the lowest score
7. **Win**: Lowest total score wins the round!

## 🔧 Development

### Running in Development Mode

```bash
# Install dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Game State Management

The game uses in-memory state management with:
- `rooms`: Dictionary of active game rooms
- `active_connections`: WebSocket connections
- Real-time state synchronization via WebSockets

### WebSocket Events

- `join_room`: Player joins a room
- `start_game`: Begin the game
- `draw_card`: Draw from deck or discard
- `replace_card`: Replace hand card with drawn card
- `discard_drawn`: Discard without replacing
- `use_special`: Activate special card powers
- `chat`: Send chat messages

## 🤝 Contributing

This is a learning project! Feel free to:
- Report bugs
- Suggest improvements
- Add new features
- Improve the UI/UX

## 📝 License

This project is for educational purposes. Feel free to use and modify as needed.

---

**Enjoy playing Ban'd!** 🎉 