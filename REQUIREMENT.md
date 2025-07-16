# Ban'd

Similar to the Cabo game, create an online game I can play cabo with friends

This game uses a standard deck of cards (excluding Joker cards)

The rules of the game is as follows.
1. Players (max of 4) start with 4 cards each
2. Players can view the bottom two cards, they must remember their cards
3. The first player to go will be random each game start
4. The first player has 2 options (1) Draw a card from the discard pile, or draw a card from the card pile. If they select a card they must replace it with one of their cards. Note: they only know two of the 4 cards
5. Players can discard their drawn card as well
6. Players will continue going around in turns drawing cards and switching from their 4 cards. The goal of the game is to have the lowest number from their combined cards.
7. Aces count as 0, red kings (2 cards) are -5 points, and cards 7-9 have special powers
8. 7 = "View one of your own cards", 8="View another players card", 9="Without viewing a card you can swap any two cards on the table"


## Technical implementation
Make a web application which allows players to create lobbies of rooms of 4. For now let's now handle authentication, only require users to enter a nickname when playing.

Use a minimal UI framework (HTMX might be cool to use). And use a python backend to handle web sockets and a performant and responsive exprience. Allow users to play in real-time and even implement a chat feature as well. We do not want to persist anything long term, we only want to keep track of the game state for now.

## Design

We want the design of the page to look modern and refined. 