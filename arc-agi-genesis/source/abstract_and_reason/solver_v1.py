# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import json
import importlib
from transformers import AutoTokenizer, AutoModelForCausalLM
from abstract_and_reason.assets import load_json
from abstract_and_reason.graphics import Graphics
import abstract_and_reason.dsl.solvers as solvers
from abstract_and_reason.dsl.primitives import find_function_names
import inspect

import numpy as np


class Solver:
    """
    Solver class for implementing solutions to ARC-AGI challenges.

    This class provides methods to load and display challenge data, predict puzzle outputs,
    and evaluate the performance of a model.
    """

    def __init__(self, prod=False) -> None:
        self.graphics = Graphics()

        if prod:
            self.base_path = '/kaggle/input/arc-prize-2024/'
        else:
            self.base_path = '../data/challenges/'

        self.training_challenges = load_json(
            self.base_path + 'arc-agi_training_challenges.json')
        self.training_solutions = load_json(
            self.base_path + 'arc-agi_training_solutions.json')
        self.evaluation_challenges = load_json(
            self.base_path + 'arc-agi_evaluation_challenges.json')
        self.evaluation_solutions = load_json(
            self.base_path + 'arc-agi_evaluation_solutions.json')
        self.test_challenges = load_json(
            self.base_path + 'arc-agi_test_challenges.json')
        self.sample_submission = load_json(
            self.base_path + 'sample_submission.json')
        
        # Load model directly
        from transformers import AutoTokenizer, AutoModelForCausalLM

        self.tokenizer = AutoTokenizer.from_pretrained("stabilityai/stable-code-3b")
        self.model = AutoModelForCausalLM.from_pretrained(
            "stabilityai/stable-code-3b",
            device_map="cpu"  # Automatically assigns CUDA devices if available
        )
        
    def load_grids(self, tasknumber):
        """
        Load the grids for a specific task number, returning both train and test grids.

        Args:
            tasknumber (str): The task number as a string.

        Returns:
            tuple: A tuple containing:
                - train_grids (list): List of dicts with 'input' and 'output' grids from the training set.
                - test_grid (dict): A dict with the 'input' grid from the test set.
        """
        # Load the JSON data for the specific task
        # or use self.evaluation_challenges or self.test_challenges, as applicable
        task_data = self.training_challenges[tasknumber]

        # Extract train grids (which contain both input and output)
        train_grids = task_data.get("train", [])

        # Extract the first test grid (which contains only input)
        test_grid = task_data.get("test", [{}])[0].get("input", None)

        return train_grids, test_grid
    
    def get_solver_function(self, tasknumber):
        """Dynamically load the solver function for a specific task."""
        module_name = 'solvers'  # Adjust this if the file is named differently
        function_name = f'solve_{tasknumber}'
        solver_function = getattr(solvers, function_name)
        function_code = inspect.getsource(solver_function)
        return function_code
    
    def generate_few_shot_prompt(self, tasknumbers):
        """Generate a few-shot prompt from multiple tasks using their training examples."""
        prompt = "Given examples of input-output grids and the DSL code that solves them, write DSL code to solve the new ARC problem. Use the provided DSL primitives to construct a solution.\n"

        for tasknumber in tasknumbers:
            # Load train grids and test grid for each task
            # We only need the train grids for few-shot examples
            train_grids, _ = self.load_grids(tasknumber)

            # Retrieve the solver function's source code as a string
            solver_code = self.get_solver_function(tasknumber)
            prompt += "Here is an example of input-output grids and the DSL code that solves them:\n"
            # Add multiple examples from `train` for this task
            for example in train_grids:
                input_grid = example['input']
                output_grid = example['output']

                example_str = f"""
                Input Grid: {input_grid}
                Expected Output: {output_grid}
                """
                prompt += example_str
            prompt += f"\nDSL Program that solves the above grids: {solver_code}"

        return prompt


    def predict(self, tasknumber):
        """
        Predicts the outputs for the test puzzle based on training examples from few-shot tasks.
        """
        try:
            # Specify task numbers for few-shot examples
            tasknumbers = ['67a3c6ac']

            # Generate few-shot prompt using the training examples from multiple tasks
            few_shot_prompt = self.generate_few_shot_prompt(tasknumbers)
            few_shot_prompt += "Use the provided DSL primitives to construct a solution:\n" + " ".join(find_function_names(
                "/Users/abdelazimlokma/Desktop/Desktop/Uni/Fall 24/CS 599 AGI/Arc-Competition/arc-agi-genesis/source/abstract_and_reason/dsl/dsl.py"))

            # Load train grids and test grid for the current task
            _, test_grid = self.load_grids(tasknumber)

            # Append the few-shot examples and the final test input for the current task
            prompt = f"{few_shot_prompt}\nCurrent Task Test Input:\n{test_grid}\n Output only the DSL code needed to solve this test grid."

            # Generate output for the current test input
            output = self.generate_text(prompt)

            return output

        except Exception as e:
            print("Error in prediction:", e)
            return None


    # Define a function to generate text from a prompt
    def generate_text(self, prompt, max_length=4000, temperature=0.7):
        # Tokenize the input prompt
        input_ids = self.tokenizer(prompt, return_tensors="pt").input_ids
        input_ids.to('cpu')
        self.model.to('cpu')
        # Generate the output
        output = self.model.generate(input_ids, max_length=max_length, temperature=temperature)
        
        # Decode the output tokens to get the generated text
        generated_text = self.tokenizer.decode(output[0], skip_special_tokens=True)
        return generated_text



    def random_prediction(self, puzzle_outs_train, puzzle_inps_test):
        """
        Generates random predictions for the test puzzles by averaging the shape of the training outputs.

        Args:
            puzzle_outs_train (list): Training output puzzles.
            puzzle_inps_test (list): Test input puzzles.

        Returns:
            list: Randomly generated predictions for the test puzzles.
        """
        answers = []
        avg_shape = np.ceil(np.array([np.array(p.shape) for p in puzzle_outs_train]).mean(
            0)).astype(int)  # I took average shape of output puzzles
        for _ in range(len(puzzle_inps_test)):
            # cause 0 to 9 options as mentioned in competition
            answers.append(np.random.randint(0, 10, size=avg_shape))

        return answers

    def train(self):
        """
        Placeholder for the training logic of the model.

        Raises:
            NotImplementedError: This function is not implemented.
        """
        # raise NotImplementedError

    def validate(self):
        """
        Placeholder for the validation logic of the model.

        Raises:
            NotImplementedError: This function is not implemented.
        """
        # Have you trained a model? use this function to validate it.
        # raise NotImplementedError

    def test(self):
        """
        Placeholder for the testing logic of the model on unseen test data.

        Raises:
            NotImplementedError: This function is not implemented.
        """
        # Have you trained a model? use this function to test it.
        # raise NotImplementedError

    def display_train(self, task_id, puzzle_inps_train, puzzle_outs_train):
        """
        Displays the training input and output puzzles using the Graphics class.

        Args:
            task_id (int): ID of the task to be displayed.
            puzzle_inps_train (list): Training input puzzles.
            puzzle_outs_train (list): Training output puzzles.
        """
        self.graphics.plot_task(
            f"Train: #{task_id}", puzzle_inps_train, puzzle_outs_train,)

    def display_test(self, task_id, puzzle_inps_test, puzzle_outs_test):
        """
        Displays the test input and output puzzles using the Graphics class.

        Args:
            task_id (int): ID of the task to be displayed.
            puzzle_inps_test (list): Test input puzzles.
            puzzle_outs_test (list): Test output puzzles.
        """
        self.graphics.plot_task(
            f"Test: #{task_id}", puzzle_inps_test, puzzle_outs_test)

    def display_task(self, task_id, puzzle_inps_train, puzzle_outs_train, puzzle_inps_test, puzzle_outs_test=None):
        """
        Displays the full task, including training and test puzzles, using the Graphics class.

        Args:
            task_id (int): ID of the task to be displayed.
            puzzle_inps_train (list): Training input puzzles.
            puzzle_outs_train (list): Training output puzzles.
            puzzle_inps_test (list): Test input puzzles.
            puzzle_outs_test (list, optional): Test output puzzles. Default is None.
        """
        self.graphics.plot_full_task(f"Task #{task_id}", puzzle_inps_train,
                                     puzzle_outs_train, puzzle_inps_test, puzzle_outs_test)

    def display_board(self, task_id, board):
        """
        Displays a single puzzle board using the Graphics class.

        Args:
            task_id (int): ID of the task to be displayed.
            board (numpy.ndarray): The puzzle board to be displayed.
        """
        self.graphics.plot_board(f"Task #{task_id}", board)

    def display_side_to_side_boards(self, board_right, board_left, title, text_right, text_left, b1_cmap=None, b2_cmap=None):
        """
        Displays two boards side by side using the Graphics class.

        Args:
            board_right (numpy.ndarray): The board to display on the right.
            board_left (numpy.ndarray): The board to display on the left.
            title (str): The title for the figure.
            text_right (str): The label for the right board.
            text_left (str): The label for the left board.
            b1_cmap (matplotlib.colors.Colormap, optional): Colormap for the right board.
            b2_cmap (matplotlib.colors.Colormap, optional): Colormap for the left board.
        """
        self.graphics.plot_side_to_side_boards(
            board_right, board_left, title, text_right, text_left, b1_cmap, b2_cmap)

    def get_challenge_board(self, challenge_id, challenges, solutions, io: str, board_type: str, board_idx):
        """
        Retrieves a specific board from the challenge dataset.

        Args:
            challenge_id (int): ID of the challenge.
            challenges (dict): Challenge dataset.
            solutions (dict): Solution dataset.
            io (str): 'input' or 'output' to specify which board to retrieve.
            board_type (str): 'train' or 'test' to specify which dataset to retrieve the board from.
            board_idx (int): Index of the board to retrieve.

        Returns:
            numpy.ndarray: The requested board, or None if not found.
        """
        board = None
        if challenge_id in list(challenges):
            puzzle_inps_train, puzzle_outs_train, puzzle_inps_test, puzzle_outs_test = self.process_challenge(
                challenge_id, challenges, solutions)
            if io == 'input':
                if board_type == 'train':
                    if board_idx in range(0, len(puzzle_inps_train)):
                        board = puzzle_inps_train[board_idx]
                else:
                    if board_idx in range(0, len(puzzle_inps_test)):
                        board = puzzle_inps_test[board_idx]
            else:
                if board_type == 'train':
                    if board_idx in range(0, len(puzzle_outs_train)):
                        board = puzzle_outs_train[board_idx]
                else:
                    if board_idx in range(0, len(puzzle_outs_test)):
                        board = puzzle_outs_test[board_idx]
        return board

    def process_challenge(self, challenge_id, challenges, solutions=None):
        """
        Processes a single challenge by extracting its training and test inputs and outputs.

        Args:
            challenge_id (int): ID of the challenge to process.
            challenges (dict): Dictionary of challenges.
            solutions (dict, optional): Dictionary of solutions. If None, test solutions are not processed.

        Returns:
            tuple: Training inputs, training outputs, test inputs, and optionally test outputs if solutions are provided.
        """
        # solutions=None cause test_challenges doesn't have solutions
        # So we can use this function on test challenge as well (big brain move)
        one_challenge = challenges[challenge_id]

        puzzle_inps_train = []
        puzzle_outs_train = []
        for puzzles in one_challenge['train']:
            puzzle_inps_train.append(np.array(puzzles['input']))
            puzzle_outs_train.append(np.array(puzzles['output']))

        puzzle_inps_test = []
        for puzzles in one_challenge['test']:
            puzzle_inps_test.append(np.array(puzzles['input']))

        if solutions != None:
            one_solution = solutions[challenge_id]
            puzzle_outs_test = []
            for puzzles in one_solution:
                puzzle_outs_test.append(np.array(puzzles))

            return puzzle_inps_train, puzzle_outs_train, puzzle_inps_test, puzzle_outs_test

        else:
            return puzzle_inps_train, puzzle_outs_train, puzzle_inps_test, None
