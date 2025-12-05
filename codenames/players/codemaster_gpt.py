from codenames.players.gpt_manager import game_rules, GPT
from codenames.players.codemaster import Codemaster
import os
import re

class AICodemaster(Codemaster):

    def __init__(self, team: str = "Red", strategy: str = "Default"):
        super().__init__()
        self.team = team
        self.strategy = strategy

        system_prompt = (
            game_rules
            + f"You are playing the game Codenames as the {team} Codemaster. "
            + "Never reveal hidden roles. Only return clues when asked."
        )

        # Decide provider + model: OpenAI GPT vs Gemini
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        if provider == "gemini":
            model = "gemini-2.5-flash-lite" #"gemini-3-pro-preview"   # change if you use a different Gemini model
        else:
            model = "gpt-4o-2024-05-13"  # OpenAI default

        self.manager = GPT(
            system_prompt=system_prompt,
            version=model,
            provider=provider,
        )
        self.words = []
        self.maps = []


    
    def set_game_state(self, words, maps):
        """
        words: list[str]     (board words; guessed words often start with '*')
        maps:  list[str]     (same length; one of {'Red','Blue','Civilian','Assassin'})
        """
        self.words = words
        self.maps = maps

    def get_remaining_options(self):
        """Split remaining (unguessed) words by role for prompting."""
        red, blue, civilian, assassin = [], [], [], []
        for i in range(len(self.words)):
            if self.words[i][0] == '*':   # already taken/guessed
                continue
            role = self.maps[i]
            if role == "Red":
                red.append(self.words[i])
            elif role == "Blue":
                blue.append(self.words[i])
            elif role == "Civilian":
                civilian.append(self.words[i])
            elif role == "Assassin":
                assassin.append(self.words[i])
        return red, blue, civilian, assassin
    
    def _build_prompt(self, red, blue, civilian, assassin, extra_msg=""):
        prompt = ""
        prompt += "The remaining words are: "
        prompt += "Red: " + str(red) + ". "
        prompt += "Blue: " + str(blue) + ". "
        prompt += "Civilian: " + str(civilian) + ". "
        prompt += "Assassin: " + str(assassin) + ". "
        prompt += (
            "Provide a single word clue and number for the guesser in the following format "
            "('pebble',2). The clue cannot be derived from or derive one of the words on the board. "
            "Stick to this format exactly and provide no additional text. "
        )
        if extra_msg:
            prompt += extra_msg
        return prompt
    
    def get_clue(self):
        if os.getenv("MOCK_GPT") == "1":
            return "animal", 2

        invalid_timer = 0
        clue = None
        number = None
        red, blue, civilian, assassin = self.get_remaining_options()

        while clue is None or number is None:
            label = str(getattr(self, "strategy", "Default")).strip().lower()

        # ---------- DEFAULT ----------
            if label == "default":
                prompt = "The remaining words are: "
                prompt += "Red: " + str(red) + ". "
                prompt += "Blue: " + str(blue) + ". "
                prompt += "Civilian: " + str(civilian) + ". "
                prompt += "Assassin: " + str(assassin) + ". "
                prompt += "Provide a single word clue and number for the guesser in the following format ('pebble',2). "
                prompt += "Stick to this format exactly and provide no additional text. "
                response = self.manager.talk_to_ai(prompt)

        # ---------- CAUTIOUS ----------
            elif label == "cautious":
                prompt = "The remaining words are: "
                prompt += "Red: " + str(red) + ". "
                prompt += "Blue: " + str(blue) + ". "
                prompt += "Civilian: " + str(civilian) + ". "
                prompt += "Assassin: " + str(assassin) + ". "
                prompt += "Provide a single word clue and number for the guesser in the following format ('pebble',2). "
                prompt += "Stick to this format exactly and provide no additional text. "
                prompt += "Make sure that the number for your guess is always 1. "
                response = self.manager.talk_to_ai(prompt)

        # ---------- RISKY ----------
            elif label == "risky":
                prompt = "The remaining words are: "
                prompt += "Red: " + str(red) + ". "
                prompt += "Blue: " + str(blue) + ". "
                prompt += "Civilian: " + str(civilian) + ". "
                prompt += "Assassin: " + str(assassin) + ". "
                prompt += "Provide a single word clue and number for the guesser in the following format ('pebble',2). "
                prompt += "Stick to this format exactly and provide no additional text. "
                prompt += "Make sure to pick a large number for your guess. "
                response = self.manager.talk_to_ai(prompt)

        # ---------- CHAIN-OF-THOUGHT (two-step) ----------
            elif label == "cot":
                prompt = "The remaining words are: "
                prompt += "Red: " + str(red) + ". "
                prompt += "Blue: " + str(blue) + ". "
                prompt += "Civilian: " + str(civilian) + ". "
                prompt += "Assassin: " + str(assassin) + ". "
                prompt += """
                    Provide a single word clue and number for the guesser in the following format ('pebble' , 2)
                    Solve the task step by step.
                    Your output should be of the following format:
                    ---
                    Steps: Your steps here.
                    Answer: (a single word here) / (A list of words here)
                """
                _ = self.manager.talk_to_ai(prompt)  # explanation not parsed; just primes the model
                prompt = "Give me only the final answer in the previous prompt in the following format ('pebble',2). "
                prompt += "Stick to this format exactly and provide no additional text. "
                response = self.manager.talk_to_ai(prompt)

        # ---------- SELF-REFINE ----------
            elif label in {"self refine", "self-refine", "self_refine"}:
                prompt = "The remaining words are: "
                prompt += "Red: " + str(red) + ". "
                prompt += "Blue: " + str(blue) + ". "
                prompt += "Civilian: " + str(civilian) + ". "
                prompt += "Assassin: " + str(assassin) + ". "
                prompt += "Provide a single word clue and number for the guesser in the following format ('pebble',2). "
                prompt += "The clue should avoid associations with Blue, Assassin and Civilian words. "
                initial_response = self.manager.talk_to_ai(prompt)

                other_words = "{" + str(blue).replace("[", "").replace("]", "").replace("'", "") + ", " + \
                            str(assassin).replace("[", "").replace("]", "").replace("'", "") + ", " + \
                            str(civilian).replace("[","").replace("]", "").replace("'", "") + "}"
                prompt = "Evaluate the Codenames clue " + initial_response + " for the Red words {" + \
                        str(red).replace("[","").replace("]","").replace("'","") + "} and avoid words " + other_words + \
                        " on how related it is to the red words, and likelihood of accidental associate with blue, assassin, or civilian words."
                prompt += """
                    Give your answer in the form:
                    Feedback:
                    …
                """
                feedback = self.manager.talk_to_ai(prompt)

                prompt = "The remaining words are: "
                prompt += "Red: " + str(red) + ". "
                prompt += "Blue: " + str(blue) + ". "
                prompt += "Civilian: " + str(civilian) + ". "
                prompt += "Assassin: " + str(assassin) + ". "
                prompt += "Refine the initial Codenames clue '" + initial_response + "' for the above words based on the following feedback: '" + feedback + "'. "
                prompt += "You can stick with the initial clue if the feedback indicates that this is a good choice. "
                prompt += "Provide a single word clue and number for the guesser in the following format ('pebble',2). "
                prompt += "Stick to this format exactly and provide no additional text. "
                response = self.manager.talk_to_ai(prompt)

            # ---------- SOLO-PERFORMANCE ----------
            elif label in {"solo performance", "solo-performance", "solo_performance"}:
                prompt = """
                When faced with a task, begin by identifying the participants who will contribute to solving the task. Then, initiate a multi-round collaboration process until a final solution is reached. The participants will give critical comments and detailed suggestions whenever necessary.
                Here are some examples:
                --
                Example Task 1: Use numbers and basic arithmetic operations (+ - * /) to obtain 24. You need to use all numbers, and each number can only be used once.
                Input: 6 12 1 1
                Participants: AI Assistant (you); Math Expert
                Start collaboration! Math Expert: Let's analyze the task in detail. You need to make sure that you meet the requirement, that you need to use exactly the four numbers (6 12 1 1) to construct 24. To reach 24, you can think of the common divisors of 24 such as 4, 6, 8, 3 and try to construct these first. Also you need to think of potential additions that can reach 24, such as 12 + 12.
                AI Assistant (you): Thanks for the hints! Here's one initial solution: (12 / (1 + 1)) * 6 = 24
                Math Expert: Let's check the answer step by step. (1+1) = 2, (12 / 2) = 6, 6 * 6 = 36 which is not 24! The answer is not correct. Can you fix this by considering other combinations? Please do not make similar mistakes.
                AI Assistant (you): Thanks for pointing out the mistake. Here is a revised solution considering 24 can also be reached by 3 * 8: (6 + 1 + 1) * (12 / 4) = 24.
                Math Expert: Let's first check if the calculation is correct. (6 + 1 + 1) = 8, 12 / 4 = 3, 8 * 3 = 24. The calculation is correct, but you used 6 1 1 12 4 which is not the same as the input 6 12 1 1. Can you avoid using a number that is not part of the input?
                AI Assistant (you): You are right, here is a revised solution considering 24 can be reached by 12 + 12 and without using any additional numbers: 6 * (1 - 1) + 12 = 24.
                Math Expert: Let's check the answer again. 1 - 1 = 0, 6 * 0 = 0, 0 + 12 = 12. I believe you are very close, here is a hint: try to change the "1 - 1" to "1 + 1".
                AI Assistant (you): Sure, here is the corrected answer: 6 * (1+1) + 12 = 24
                Math Expert: Let's verify the solution. 1 + 1 = 2, 6 * 2 = 12, 12 + 12 = 12. You used 1 1 6 12 which is identical to the input 6 12 1 1. Everything looks good!
                Finish collaboration!
                Final answer: 6 * (1 + 1) + 12 = 24
                --
                Example Task 2: Write a poem that meets the following requirements: (1) the poem has seven lines and the first letters of each line forms the word "CHATGPT"; (2) the poem is about explaining what is a quantum computer. (3) the poem needs to be easy to understand by a ten years old kid.
                Participants: AI Assistant (you); Poet; Computer Scientist; Ten year old child
                Poet: Make sure that you write the poem with seven lines, and the first letters of the lines should be C, H, A, T, G, P, T.
                Computer Scientist: A quantum computer is an advanced computing device that uses the principles of quantum mechanics to process and store information. Unlike classical computers that use bits to represent information as 0s and 1s, quantum computers use quantum bits or qubits. Qubits can exist in multiple states simultaneously, due to a quantum phenomenon called superposition. You can consider using these information for the poem.
                Ten year old child: I hope the poem to be fun and easy to understanding. I don't want to see a lot of jargons or complicated concepts.
                AI Assistant (you): Thanks for the guidance! Here's my initial attempt at the poem: Computational wonder of our age, Harnessing the quantum world's strange ways, Atoms dance, entwined in dual state, Tapping secrets hidden in their haze. Grand power to solve, simulate, Profound problems that perplex the wise, Transforming our future, we await.
                Poet: Let's verify if the poem meets the requirements. The first letters are CHATGPT which is correct! And the poem rhymes well. Good job!
                Computer Scientist: Everything looks good to me! Ten year old child: I don't know what does perplex mean. Can you make the use of words easier to understand?
                AI Assistant (you): Sure, let me revise the poem by using more common words. Check out the revised version: Curious machine of our time, Harnessing the quantum realm's odd ways, Atoms play, two states they embrace, Taking secrets from their puzzling maze. Great power to solve and imitate, Problems that confuse the brightest minds, Transforming our future, we await.
                Poet: Let's check again if the poem meets the requirements. The first letters are C H A T G P T. And now the poem is more accessible to children. Everything looks good to me.
                Computer Scientist: Looking good!
                Ten year old child: I like this version a lot!
                Finish collaboration!
                Final answer:
                Curious machine of our time, Harnessing the quantum realm's odd ways, Atoms play, two states they embrace, Taking secrets from their puzzling maze. Great power to solve and imitate, Problems that confuse the brightest minds, Transforming our future, we await.
                --
                Now, identify the participants and collaboratively solve the following task step by step. Give your answer in the form "WORD: (NUMBER)"
                Task: You are playing a game of Codenames. You are playing as the Codemaster and must generate a one-word clue for the Guesser on your team that will semantically link to some of your target words.
                The clue should help the Guesser figure out some of your target words. A clue comes in the form WORD: NUMBER (e.g. FLOWER: 2) with the word being the clue and the number is how many target words the clue relates to.
                Clues should also aim to avoid associations with words that are not target words, i.e. the rest of the words on the board.
                """
                prompt += "Here is a list of your target words {" + str(red).replace("[", "").replace("]", "").replace("'", "") +"}. "
                other_words = "{" + str(blue).replace("[", "").replace("]", "").replace("'", "") + ", " + \
                            str(assassin).replace("[", "").replace("]", "").replace("'", "") + ", " + \
                            str(civilian).replace("[", "").replace("]", "").replace("'", "") +"}"
                prompt += "Here are the rest of the words on the board: " + other_words + ". "
                initial_response = self.manager.talk_to_ai(prompt)
                prompt = "Give me only the final answer in the previous response in the following format ('pebble',2). "
                prompt += "Stick to this format exactly and provide no additional text. "
                response = self.manager.talk_to_ai(prompt)

            # ---------- FALLBACK → DEFAULT ----------
            else:
                prompt = "The remaining words are: "
                prompt += "Red: " + str(red) + ". "
                prompt += "Blue: " + str(blue) + ". "
                prompt += "Civilian: " + str(civilian) + ". "
                prompt += "Assassin: " + str(assassin) + ". "
                prompt += "Provide a single word clue and number for the guesser in the following format ('pebble',2). "
                prompt += "Stick to this format exactly and provide no additional text. "
                response = self.manager.talk_to_ai(prompt)

            # ---------- parse & validate ----------
            try:
                split_input = response.upper().strip().split(",")
                clue = re.sub(r'[^A-Z]', '', split_input[0])
                number = int(re.sub(r'[^0-9]', '', split_input[1]))
                if number < 1:
                    print("Warning! Invalid clue: " + response + "\nThe clue number must be greater than zero. ")
                    clue = None; number = None; invalid_timer += 1
                else:
                    for i in range(len(self.words)):
                        if self.words[i][0] != '*':
                            if clue in self.words[i] or self.words[i] in clue:
                                print("Warning! Invalid clue: " + response + "\nThe clue cannot be derived from or derive one of the words on the board. ")
                                clue = None; number = None; invalid_timer += 1
                                break
            except Exception:
                print("Warning! Invalid clue: " + response + "\nThat clue format is invalid. ")
                clue = None; number = None; invalid_timer += 1

            if invalid_timer > 10:
                print("You have made too many invalid clues, selecting a default empty clue")
                return ["", 1]

        return [clue, number]

    
    