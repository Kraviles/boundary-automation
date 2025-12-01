# ♦️ Project Penney 

## ♠️ Description

Penney's Game is a two player coin tossing game where each player will choose a sequence of heads (H) and tails (T) and the player with their sequence to first appear in the sequence of consecutive coin flips wins. 

Other variations of this game exist such as [Humble-Nishiyama Randomness Game](https://mathwo.github.io/assets/files/penney_game/humble-nishiyama_randomness_game-a_new_variation_on_penneys_coin_game.pdf)  which utilizes an ordinary deck of playing cards and follows the same format using red and black cards rather than heads and tails and the game iterates through the entire deck of cards. Each player chooses a sequence of three colors (e.g. player one chooses RRR and player two chooses BBB), and then starts the game by dealing the deck until the sequence appears. 

The game can either be scored by cards or by tricks, if its by tricks, the player who has the most tricks (the collection of played cards) gets one point, and if its by cards, the player who has the most cards at the end of the deck gets one point. This is a more cumulative approach rather than looking at first occurrence like in Penney's Game. It is also different compared to Penney's Game due to the finite nature of a deck, which allows us to show how player 2's odds of winning are increased. 

The purpose of this project is to understand the strategy of choice in the game, and how it differs from scoring by cards or by tricks. The strategy that we are testing is if player two chooses not player one's second choice, then player one's first choice and lastly player one's second choice. For example, if player one chose **RRR**, player two would subsequently choose **BRR**, since the strategy goes (not 2 - 1 - 2). By running millions of simulated decks, the program estimates the probability of winning for every pair of sequences with each scoring rule.

As mentioned before, due to the finite nature of the deck, and how the game is played without replacement, probabilities shift as cards are drawn. Using the example above, if you draw a red, the deck now has relatively more black cards left in the deck. When tossing a coin, combinations can appear infinitely often. However, with the Humble-Nishiyama game and our code, we aim to demonstrate this difference in probability and strategy choice. 


## ♥️ Quick-Start Guide

This project is managed using [UV](https://docs.astral.sh/uv/). If you do not yet have UV installed or need help troubleshooting issues with UV, refer to their [documentation](https://docs.astral.sh/uv/getting-started/features/). 

Once UV is installed, download the repository, navigate to the directory and run: `uv sync` to install dependencies.

Run the program

`uv run main.py -- augment 5000000` to create 5000000 new decks and automatically update scores and figures.

## ♣️ Project Structure

`main.py`: The main script to run the full data generation and scoring pipeline.

`src/data_gen.py`: Contains functions for generating simulated card decks.

`src/score.py`: Implements the scoring method.

`src/viz.py`: Implements the visualization method.

`raw_data/`: The directory where raw deck data is stored.

`results/`: The default directory for output CSV files.

`Scoring.md`: A detailed document describing and comparing the two scoring methods.

`viz.md`: A detailed document describing the visualization method.
