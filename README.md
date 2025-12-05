# Codenames AI Competition Framework
This is the Codenames AI Competition Framework. In this version, the focus is on LLM-based Codemaster and Guesser agents (OpenAI + Gemini) and course/research experiments for the game "Codenames" by Vlaada Chvátil. There are a large number of AI competitions built around games (and even more platforms using games as a testbed for AI), but with few exceptions these have focused on things that AI is likely to be good at (fine, pixel-perfect control or search through a large state space). The purpose of this framework is to test AI in a framework that:

* Requires the understanding of language
* Requires communication, in a semantically meaningful way, with another agent (Codemaster/Guesser)
* Requires understanding words with multiple meanings and avoiding dangerous associations (e.g., Assassin)
* Supports LLM Codemaster–Guesser agents with multiple prompt-engineering strategies

**Further installation requirements are found below.**

## Submissions
The original version of this codebase was used for an open AI competition.
In this fork, it is primarily used for course projects and experiments.

You can still “submit” agents to the framework by:
* Implementing a Codemaster bot as a Python 3 class that derives from Codemaster (in codemaster.py), and
* Implementing a Guesser bot as a Python 3 class that derives from Guesser (in guesser.py), and then run from the Streamlit dashboard (ui_app.py).

The setup in this project is:
* Codemaster: codenames.players.codemaster_gpt.AICodemaster
* Guesser: codenames.players.guesser_gpt.AIGuesser with a chosen prompt strategy (e.g., Default, Cautious, Risky, COT, Self Refine, Solo Performance).

## Running the game from the Streamlit dashboard

The main way to run experiments in this version is via the Streamlit UI. 
* From the repository root: streamlit run ui_app.py
* This launches a web app titled “Codenames GPT”.
  * Sidebar controls
    In the left sidebar, under “Run a new game”, you can configure:
    Backend - A radio button:
    * Mock (no API calls) – uses a simple mock GPT for fast debugging
    * OpenAI (GPT-4o) – uses OpenAI (model selected in the GPT agents)
    * Gemini – uses Gemini (model selected in the GPT agents)
    The selected backend sets the LLM_PROVIDER environment variable so that gpt_manager.py knows whether to use OpenAI or Gemini.In Mock mode, MOCK_GPT=1 is set in the environment and no real API calls are made.
  * Strategies - it has two dropdowns:
    * Codemaster strategy (for AICodemaster)
    * Guesser strategy (for AIGuesser)
    Supported strategy labels shared by Codemaster and Guesser are Default, Cautious, Risky, COT, Self Refine, Solo Performance.
  * Single game vs batch of 10 fixed boards
    * Checkbox: Use my 10 fixed boards (batch) and it runs the chosen Codemaster/Guesser strategy pair on 10 predefined seeds, stored in       FIXED_BOARD_SEEDS in ui_app.py.
    * Unchecked → run a single game on a random seed (seed="time").
  * Run button: A caption under the button shows where the run will be saved, e.g.:Saves to: results/NoMockMode/CM-Default__G-Default

## What is displayed
In the main panel, the UI displays:
* The 5×5 board of Codenames words.
* Optional reveal of the underlying roles (Red, Blue, Civilian, Assassin).
* A legend explaining tile colors.
* A timeline of events (start, each clue, each guess).
* A summary showing:
  * Seed
  * Win / loss
  * Number of turns
  * Score (including “paper-style” score: turns for wins, 25 for losses)
* The UI also maintains an aggregated statistics file (results/tech_stats.json) with:
  * Number of runs, wins, losses
  * List of turns per run
  * “Paper-style” scores (turns if win, 25 if loss), following the CoG 2024 scoring scheme with separate buckets for:
     * Mock (mock GPT runs)
     * OpenAI (OpenAI backend)
     * Gemini (Gemini backend).


## Game Class

The main framework class that calls your AI bots.

As mentioned above, a Game can be created/played directly by importing game.Game,
initializing with the args below, and calling the run() method.

```
Class that setups up game details and 
calls Guesser/Codemaster pair to play the game

Args:
    codemaster (:class:`Codemaster`):
        Codemaster (spymaster in Codenames' rules) class that provides a clue.
    guesser (:class:`Guesser`):
        Guesser (field operative in Codenames' rules) class that guesses based on clue.
    seed (int or str, optional): 
        Value used to init random, "time" for time.time(). 
        Defaults to "time".
    do_print (bool, optional): 
        Whether to keep on sys.stdout or turn off. 
        Defaults to True.
    do_log (bool, optional): 
        Whether to append to log file or not. 
        Defaults to True.
    game_name (str, optional): 
        game name used in log file. Defaults to "default".
    cm_kwargs (dict, optional): 
        kwargs passed to Codemaster.
    g_kwargs (dict, optional): 
        kwargs passed to Guesser.
```

## Codemaster Class
Any Codemaster bot is a python 3 class that derives from the supplied abstract base class Codemaster in `codemaster.py`.  The bot must implement three functions:
```
__init__(self)
set_game_state(words_on_board : List[str], key_grid : List[str]) -> None
get_clue() -> Tuple[str,int]
```
#### *details*

'__init__' sets up any internal state your Codemaster needs.
In this LLM-based version, for example, AICodemaster takes:
* team (e.g., "Red")
* strategy (e.g., "Default", "Cautious", "Risky", "COT", "Self Refine", "Solo Performance")
and constructs a GPT manager from gpt_manager.py with an appropriate system prompt.

`set_game_state` is passed the list of words on the board, as well as the key grid provided to spymasters (codemasters).  The `words` are either: an all upper case word found in the English language or one of 4 special tokens: `'*Red*', '*Blue*', '*Civilian*', '*Assassin*'` indicating that the word that was originally at that location has been guessed and been found to be of that type.  The `key_grid` is a list of `'*Red*', '*Blue*', '*Civilian*', '*Assassin*'` indicating whether a spot on the board is on the team of the codemaster (`'*Red*'`), the opposing team (`'*Blue*'`), a civilian (`'*Civilian*'`), or the assassin (`'*Assassin*'`).

`get_clue` returns a tuple containing the clue, a single English word, and the number of words the Codemaster intends it to cover.
In codemaster_gpt.AICodemaster, this is produced by prompting an LLM with the remaining board state and the chosen strategy.

## Guesser Class

Any Guesser bot is a python 3 class that derives from the supplied abstract base class Guesser in `guesser.py`.  The bot must implement four functions:

```
__init__(self)
set_board(words: List[str]) -> None
set_clue(clue: str, num_guesses: int) -> None
keep_guessing -> bool
get_answer() -> Str
```

#### *details*

`__init__` is analogous to the Codemaster, and in the GPT-based Guesser (AIGuesser) is used to set up the GPT manager and a strategy label.

`set_board` is passed the list of words on the board.  The `words` are either: an all upper case word found in the English language or one of 4 special tokens: `'*Red*', '*Blue*', '*Civilian*', '*Assassin*'` indicating that the word that was originally at that location has been guessed and been found to be of that type.

`set_clue` is passed the clue and the number of guesses it covers, as supplied by the `get_clue` of the codemaster through the Game class.

`keep_guessing` is a function that the game engine checks to see if the bot chooses to keep guessing, as the bot must only make at least one guess, but may choose to guess until it has gone to the number supplied by get_clue + 1. In the GPT-based Guesser, some strategies (e.g. Cautious / Risky) use simple numeric rules, while others (e.g. Default / COT / Self Refine / Solo Performance) ask the LLM whether to continue.

`get_answer` returns the current guess of the Guesser, given the state of the board and the previous clue.

In guesser_gpt.AIGuesser, the LLM is prompted to return exactly one board word, which is then normalized and matched against the remaining words on the board.



## Rules of the Game

Codenames is a game of language understanding and communication.  The competition takes place in a single team style of play -- The Codemaster and Guesser are both on the Red team, and their goal is to discover their words as quickly as possible, while minimizing the number of incorrect guesses.

At the start of the game, the board consists of 25 English words:

DAY SLIP SPINE WAR CHICK
FALL HAND WALL AMAZON DEGREE
GIANT CENTAUR CLOAK STREAM CHEST
HAM DOG EMBASSY GRASS FLY
CAPITAL OIL COLD HOSPITAL MARBLE

The Codemaster has access to a hidden map that tells them the identity of all of the words:

*Red* *Red* *Civilian* *Assassin* *Red*
*Red* *Civilian* *Red* *Civilian* *Civilian*
*Civilian* *Civilian* *Civilian* *Blue* *Civilian*
*Red* *Civilian* *Red* *Red*

Meaning that the words that Codemaster wants their teammate to guess are:

DAY, SLIP, CHICK, FALL, WALL, CAPITAL, HOSPITAL, MARBLE

The Codemaster then supplies a clue and a number (the number of guesses the Guesser is obligated to make):

e.g., `('pebble',2)`

The clue must:
* Be semantically related to what the Codemaster wants their guesser to guess -- no using words to tell the position of the words
* Be a single English word
* NOT be derived from or derive one of the words on the board -- i.e. days or cloaked are not valid clues

The guesser then returns a list of their guesses, in order of importance:

e.g. `['MARBLE', 'STREAM']`

This would result in them guessing 1 word correctly -- MARBLE -- and guessing one that is linked to a civilian -- STREAM.  If instead the guesser had guessed:

`['STREAM', 'MARBLE']`

Then the result would be in 1 incorrect guess -- STREAM -- and their turn would have ended at that point.  It is important for the guesser to correctly order their guesses, as ordering is important.

If a guesser guesses an invalid clue, their turn is forfeit.

Play proceeds, passing back and forth, until one of 3 outcomes is achieved:

* All of the Red tiles have been found -- the team wins
* All of the Blue tiles have been found -- the team loses
* The single *Assassin* tile is found -- the team loses

## Competition Rules

Competition results will be scored by the number of turns required to guess all 8 red words. Scores will be calculated in an inverse proportional fashion, so the lower the better. 

* The average number of turns the codemaster/guesser takes will be the score given to each paired bot.
* Guessing an assassin-linked word or the 7 blue words before all 8 red words will result in an instant loss and a score of 25 turns or points.

Codemaster bots will be swapped and trialed with multiple guessers and conversely guesser bots will be swapped with codemasters to ensure and maximize variability and fairness.

In other words you'll be paired up with other player's bots, and scored/tested to see how well your AI can perform within a more general context of Natural Language Understanding.

## Prerequisite: Installation and Downloads
Note: The installation of the [Anaconda Distribution](https://www.anaconda.com/distribution/) should be used for certain dependencies to work without issues. Also installing NLTK and gensim through conda is much simpler and less time consuming than the below alternatives.

Example installation order:
```
(base) conda create --name codenames python=3.10
(base) conda activate codenames
(codenames) pip install streamlit openai google-genai

```
You also need the Codenames project files (this repository), which include:
* run_game.py
* ui_app.py
* codenames/game.py
* codenames/players/codemaster.py, codenames/players/guesser.py
* codenames/players/codemaster_gpt.py, codenames/players/guesser_gpt.py
* codenames/players/gpt_manager.py
Make sure the repository root is on your PYTHONPATH (for example, by running commands from the repo root or installing it as a package).
To check that everything is installed without error, you can run something like: python -c "import streamlit, openai, google"

The original framework also depended on gensim, nltk, and large word vector files (GloVe, Google News word2vec) for vector-based bots. These are not required if you only use the GPT-based LLM agents.

## OpenAI & Gemini GPT Agents
The GPT-based Codemaster and Guesser are implemented in:
* codenames.players.codemaster_gpt.AICodemaster
* codenames.players.guesser_gpt.AIGuesser
Both use the GPT wrapper defined in gpt_manager.py.

## API keys and provider selection
Instead of editing the source file to add API keys, this version uses environment variables.
Set the following before running:
* OpenAI : export OPENAI_API_KEY="your-openai-key"
* Gemini : export GEMINI_API_KEY="your-gemini-key"
* Provider : export LLM_PROVIDER="openai"   # or "gemini"
When using the Streamlit UI, the sidebar “Backend” radio button automatically sets LLM_PROVIDER for you.

After setting the environment variables, you can run the GPT agents via: Streamlit UI as described above.


