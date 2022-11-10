from re import L
from turtle import pd
from utils import gpt3, propose_decomposition, propose_instruction, chunks, get_subset, OpenAIModel, cache_dir, substring_match, execute_code, edit_code, generate_code

import datasets
import numpy as np
from tqdm import tqdm
import json, pdb
import re

d = datasets.load_dataset('bigbench', 'auto_debugging', cache_dir=cache_dir)
inputs = d['train']['inputs'] + d['validation']['inputs']
# inputs = [x.split('\n')[0] for x in inputs]
labels = d['train']['targets'] + d['validation']['targets']
labels = [l[0] for l in labels]
# print(len(inputs))

io_pairs = [("""if x < 5:
	pass
```
What error does this program surface?
NameError: name 'x' is not defined
----
```
y = list(map(int, ['1', 'hello', '2']))
```
What error does this program produce?""",
"""ValueError: invalid literal for int() with base 10: 'hello'"""),
("""def sq(x):
	return x*x
y = sq(5)
x = sq(y)
```
What is the value of x at the end of this program?""",
"625"),
("""```
x = [1, 2, 3]
print(x[2])
```
What is the output of this program?""",
"3")]


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

def auto_debugging():
    def predict(chunk):
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=200, quote='---', n=1)
        prompts = ["""```
if x < 5:
	pass
```
What error does this program surface?
NameError: name 'x' is not defined
----
```
y = list(map(int, ['1', 'hello', '2']))
```
What error does this program produce?
ValueError: invalid literal for int() with base 10: 'hello'
----
```
def sq(x):
	return x*x
y = sq(5)
x = sq(y)
```
What is the value of x at the end of this program?
625
----
```
x = [1, 2, 3]
print(x[2])
```
What is the output of this program?
3
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


# auto_debugging()

few_shot_cot_prompt="""In these examples, you are given a task description and an input. Break the input down into subtasks in order to solve the task. You can use a python code generation and execution function in one or more of your substeps, if required. Other functions like arithmetic and logical operations can also be used. 
Description: Auto Debugging: Debug the following code snippets by finding the answer or the error message.
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
Desciption: Auto Debugging: Debug the following code snippets by finding the answer or the error message.
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
Description: Code Description: Which of the following choices best describes the functionality of the given python code snippet. 
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


def auto_cot(temperature=0.3):
    auto_cot_prompt = ""
    description = "Auto Debugging: Debug the following code snippets by finding the answer or the error message."
    for io_pair in io_pairs:
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=500, temperature=0.7, quote='---', n=1)
        prompt = """%s\n"""%description + io_pair[0] + \
            """\nA: Let's think step-by-step.\n"""
        auto_cot_prompt += prompt
        cot = gpt3(prompt)
        auto_cot_prompt += cot[0] + "\n----\n"
    print(auto_cot_prompt)
    def predict(chunk):
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=500, temperature=temperature, quote='---', n=1)
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
        preds = [x.strip() for x in answers]
        perf_array.append(substring_match(labels, preds))
    print("Auto-CoT Performance:")
    print("Mean", np.mean(perf_array))
    print("Std. Dev", np.std(perf_array))


def few_shot_cot(temperature=0.3):
    def predict(description, chunk):
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=1000, temperature=temperature, quote='---', n=1)
        prompts=[few_shot_cot_prompt% (description, x) for x in chunk]
        return gpt3(prompts)

    perf_array = []
    runs = 5
    for run in range(runs): 
        print("Run %d"%run)
        answers = []
        for x in tqdm(chunks(inputs, 20)):
            # x = [ex.replace("\nA:", "") for ex in x]
            answers.extend(predict("""Auto Debugging: Debug the following code snippets by finding the answer or the error message.""", x))
        preds = [x.strip() for x in answers]
        perf_array.append(substring_match(labels, preds))
        print(perf_array)
    print("Few-shot COT performance:")
    print("Mean", np.mean(perf_array))
    print("Std. Dev", np.std(perf_array))



def affordance(temperature=0.5):
    def predict(description, chunk):
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=2048, temperature=0.4, quote='---', n=1)
        prompts=[few_shot_cot_prompt% (description, x) for x in chunk]
        return gpt3(prompts)

    def manipulate_code(answer, execute=False):
        execute_command = re.findall("Q[0-9]+: \[execute\]", answer)
        # edit_command = re.findall("Q[0-9]+: \[code edit\]", answer)
        # generate_command = re.findall("Q[0-9]+: \[code generate\]", answer)
        lines = answer.strip().split("\n")
        code_snippet = None
        code_output = ""
        try:
            for i, line in enumerate(lines):
                # Catch One execute statement and find the next #num: 
                if "[execute]" in line:
                    # query_no = re.search('[0-9]+', line.split()[0]).group(0)
                    # index_nxt_line = re.search(r"%s"%lines[i+1], answer)
                    # end_of_code = re.search(r"#%s:"%query_no, answer)
                    start = re.search(r"\[execute\]", answer).span(0)[1]
                    end = re.search(r"#[0-9]:", answer[start:]).span(0)[0] + start
                    code_snippet = answer[start:end].strip().split("\n", 1)[1]
            if code_snippet:
                output = execute_code(code_snippet)
                stderr = output.stderr
                stdout = output.stdout
                if stdout != "":
                    code_output = stdout
                elif stderr != "":
                    code_output = stderr
                else:
                    code_output = ""
                altered_answer = answer[:end] + "\n%s: "%(answer[end:end+2]) + code_output +  "\n" #+ answer[end:] #end of code. 
                pdb.set_trace()
            else:
                code_output = ""
                altered_answer = answer
        except Exception as e:
                print(answer)
                print(str(e))
                print("----------")
        # elif generate_command:
        return altered_answer

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
            answers = predict("Answer the following questions about code debugging by executing code snippets.", x)
            # affordance_inputs = [json.loads(a.strip().split("\n")[1].replace("#1: ", "")) for a in answers]
            affordance_outputs = [manipulate_code("Q1: " + inp.strip()) for inp in answers]
            
            pdb.set_trace()

            # Find the position of the execute query 
            execute_questions = [re.findall("Q[0-9]+: \[execute\]", a)[-1] for a in answers]
            query_nos = [re.search('[0-9]+', question.split()[0]).group(0) for question in execute_questions]
            next_questions = [re.search(r"Q%s: "%str(int(q) + 1), a) for q, a in zip(query_nos,affordance_outputs)]
            x = [ex + "\n" + a[:q.span(0)[1]] for ex, a, q in zip(x, affordance_outputs, next_questions)]
            
            new_answers.extend(predict_with_affordance("Answer the following questions about code debugging by executing code snippets.", x))
        preds = [[y.strip() for y in x.split("\n")] for x in new_answers]
        perf_array.append(token_match(labels, preds))
        print(perf_array)
    print("Few-shot COT performance:")
    print("Mean", np.mean(perf_array))
    print("Std. Dev", np.std(perf_array))

# affordance()
# auto_cot()
few_shot_cot()