from re import L
from turtle import pd
from utils import gpt3, propose_decomposition, propose_instruction, chunks, get_subset, OpenAIModel, cache_dir, substring_match

import datasets
import numpy as np
from tqdm import tqdm
import json, pdb
import re


io_pairs=[("""Given two strings, determine the length of the longest common subsequence.

Strings: VIRVRHRSTQBLLSYPZDVYCFPSQRXNA SPLYVHLWMLDJVYMQTOZMVOJF
Length of longest common subsequence:""",
"8"),
("""Given two strings, determine the length of the longest common subsequence.

Strings: SCZFZGCCQQLB OJDXI
Length of longest common subsequence:""",
"0"),
("""Given two strings, determine the length of the longest common subsequence.

Strings: RLXEHVGPC LDOOBAOCQPRJKZWOKUPPEHEAZIZPLSB
Length of longest common subsequence:""",
"4"),
("""Determine whether the given sequence of parentheses is properly matched.

Sequence: } { ( [
Valid/Invalid?""",
"Invalid"),
("""Determine whether the given sequence of parentheses is properly matched.

Sequence: [ [ [ { [ [ ] { { } ( ) } [ ] ] } ] ] ]
Valid/Invalid?""",
"Valid"),
("""Determine whether the given sequence of parentheses is properly matched.

Sequence: [ { } ]
Valid/Invalid?""",
"Valid"),
("""Determine whether the given sequence of parentheses is properly matched.

Sequence: ) } { [ ) } [ } { )
Valid/Invalid?""",
"Invalid"),
("""Determine whether the given sequence of parentheses is properly matched.

Sequence: ( ) [ ( ) ] ( { } )
Valid/Invalid?""",
"Valid"),
("""Determine whether the given sequence of parentheses is properly matched.

Sequence: [ {
Valid/Invalid?""",
"Invalid"),
("""Determine whether the given sequence of parentheses is properly matched.

Sequence: [ { } ] { } { [ ] [ ] } [ ] ( { ( ) } )
Valid/Invalid?""",
"Valid")]

d = datasets.load_dataset('bigbench', 'cs_algorithms', cache_dir=cache_dir)
inputs = d['validation']['inputs']
# inputs = [x.split('\n')[0] for x in inputs]
labels = d['validation']['targets']
labels = [l[0] for l in labels]

def exact_match(labels, predictions):
    correct = 0
    count = 0
    for label, predict in zip(labels, predictions):
        if label.lower() == predict.lower():
            correct += 1
        count += 1
    return (1.0*correct)/count

def token_match(labels, predictions):
    correct = 0
    count = 0
    for label, predict in zip(labels, predictions):
        if label.lower() in [p.lower() for p in predict]:
            correct += 1
        count += 1
    return (1.0*correct)/count

def cs_algorithms():
    def predict(chunk):
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=200, quote='---', n=1)
        prompts = ["""Given two strings, determine the length of the longest common subsequence.

Strings: VIRVRHRSTQBLLSYPZDVYCFPSQRXNA SPLYVHLWMLDJVYMQTOZMVOJF
Length of longest common subsequence:
8
----
Given two strings, determine the length of the longest common subsequence.

Strings: SCZFZGCCQQLB OJDXI
Length of longest common subsequence:
0
----
Given two strings, determine the length of the longest common subsequence.

Strings: RLXEHVGPC LDOOBAOCQPRJKZWOKUPPEHEAZIZPLSB
Length of longest common subsequence:
4
----
Determine whether the given sequence of parentheses is properly matched.

Sequence: } { ( [
Valid/Invalid?
Invalid
----
Determine whether the given sequence of parentheses is properly matched.

Sequence: [ [ [ { [ [ ] { { } ( ) } [ ] ] } ] ] ]
Valid/Invalid?
Valid
----
Determine whether the given sequence of parentheses is properly matched.

Sequence: [ { } ]
Valid/Invalid?
Valid
----
Determine whether the given sequence of parentheses is properly matched.

Sequence: ) } { [ ) } [ } { )
Valid/Invalid?
Invalid
----
Determine whether the given sequence of parentheses is properly matched.

Sequence: ( ) [ ( ) ] ( { } )
Valid/Invalid?
Valid
----
Determine whether the given sequence of parentheses is properly matched.

Sequence: [ {
Valid/Invalid?
Invalid
----
Determine whether the given sequence of parentheses is properly matched.

Sequence: [ { } ] { } { [ ] [ ] } [ ] ( { ( ) } )
Valid/Invalid?
Valid
----
%s
""" % x for x in chunk]
        return gpt3(prompts)

    perf_array = []
    runs = 5
    for run in range(runs): 
        print("Run %d"%run)
        answers = []
        for x in tqdm(chunks(inputs, 20)):
            answers.extend(predict(x))
        preds = [x.strip() for x in answers]
        perf_array.append(exact_match(labels, preds))
    print("No decomposition Performance:")
    print("Mean", np.mean(perf_array))
    print("Std. Dev", np.std(perf_array))


cs_algorithms()


few_shot_cot_prompt="""In these examples, you are given a task description and an input. Break the input down into subtasks in order to solve the task. You can use a python code generation and execution function in one or more of your substeps, if required. Other functions like arithmetic and logical operations can also be used. 
Description: 
Input: 
```
if x < 5:
	pass
```
What error does this program surface?
Q1: [execute] Execute the following python code snippet.
if x < 5:
	pass
#1:
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
NameError: name 'x' is not defined
Q2: What is the final error message?
#2: NameError: name 'x' is not defined
Q3: [EOC]
NameError: name 'x' is not defined
----
Desciption:
Input:
```
x = set([1, 1, 2, 3])
```
What is the value of x after this program executes?
Q1: [code edit] Edit the following code to get the value of x
x = set([1, 1, 2, 3])
#1:
x = set([1, 1, 2, 3])
print(x)
Q2: [execute] Execute the following python code snippet.
x = set([1, 1, 2, 3])
print(x)
#2: {1, 2, 3}
Q3: [EOC]
{1, 2, 3}
----
Description:
Input:
Python code:
try:
    n = int(input())
    m = int(input())
    integer_sum = int(n) + int(m)
    print(integer_sum)
except:
    print('error')

  choice: prints number between 5 and 6
  choice: try input and except error
  choice: inputs the string 'try'
  choice: prints sum of two input numbers only if they are integers otherwise raises error
Q1: [code generate] prints number between 5 and 6
#1:
import random

print(random.uniform(5,6))
Q2: [code generate] try input and except error
#2
try:
    #open file
    file = open(file_name, "r")
    #read file
    data = file.read()
    #close file
    file.close()
    #split data
    data = data.split("\n")
    #remove empty string
Q3: [code generate] inputs the string 'try'
#3: print('try')
Q4: [code generate] prints sum of two input numbers only if they are integers otherwise raises error
#4:
#!/usr/bin/python

a=raw_input("enter first number: ")
b=raw_input("enter second number: ")
try:
    sum=int(a)+int(b)
    print "sum is: ",sum
except:
    print "enter integer values only"
Q5: Which of the generated code snippets are most like the original one?
#5: prints sum of two input numbers only if they are integers otherwise raises error
Q6: [EOC]
----
Desciption: %s
Input: %s
Q1: """



def auto_cot():
    auto_cot_prompt = ""
    description = "TASK: Take the letters at position 3 of the words in a list of words and concatenate them using a space."
    for io_pair in io_pairs:
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=500, temperature=0.2, quote='---', n=1)
        prompt = """%s\n"""%description + io_pair[0] + \
            """\nA: Let's think step-by-step.\n"""
        auto_cot_prompt += prompt
        cot = gpt3(prompt)
        auto_cot_prompt += cot[0] + "\n----\n"
    print(auto_cot_prompt)
    def predict(chunk):
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=500, temperature=0.2, quote='---', n=1)
        prompts=[auto_cot_prompt + """%s\n""" %description + \
            """%s\nA: Let's think step-by-step.\n"""%x for x in chunk]
        return gpt3(prompts)

    perf_array = []
    runs = 5
    for run in range(runs): 
        print("Run %d"%run)
        answers = []
        for x in tqdm(chunks(inputs, 20)):
            x = [ex.replace("\nA:", "") for ex in x]
            answers.extend(predict(x))
            pdb.set_trace()
        preds = [x.strip() for x in answers]
        perf_array.append(substring_match(labels, preds))
    print("Auto-CoT Performance:")
    print("Mean", np.mean(perf_array))
    print("Std. Dev", np.std(perf_array))

auto_cot()


def affordance():
    def predict(description, chunk):
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=2048, temperature=0.4, quote='---', n=1)
        prompts=[few_shot_cot_prompt% (description, x) for x in chunk]
        return gpt3(prompts)

    def string_index(sequence, position):
        char_list = []
        for word in sequence:
            character  = word[position]
            char_list.append(character)
        return char_list

    def predict_with_affordance(description, chunk):
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=2048, temperature=0.4, quote='---', n=1)
        prompts=[few_shot_cot_prompt% (description, x) for x in chunk]
        return gpt3(prompts)

    perf_array = []
    runs = 5
    for run in range(runs): 
        print("Run %d"%run)
        answers = []
        new_answers = []
        for x in tqdm(chunks(inputs, 20)):
            answers = predict("Take the letters at position 3 of the words in a list of words and concatenate them using a space.", x)
            pdb.set_trace()
            affordance_inputs = [json.loads(a.strip().split("\n")[1].replace("#1: ", "")) for a in answers]
            affordance_outputs = [string_index(inp, 2) for inp in affordance_inputs]
            x = [ex + a[:re.search("#2: ", a).span(0)[1]] + json.dumps(o) for ex, a, o in zip(x, answers, affordance_outputs)]
            new_answers.extend(predict_with_affordance("Take the letters at position 3 of the words in a list of words and concatenate them using a space.", x))
        preds = [[y.strip() for y in x.split("\n")] for x in new_answers]
        perf_array.append(token_match(labels, preds))
        print(perf_array)
    print("Few-shot COT performance:")
    print("Mean", np.mean(perf_array))
    print("Std. Dev", np.std(perf_array))

affordance()