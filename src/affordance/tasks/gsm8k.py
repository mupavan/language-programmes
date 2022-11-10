from re import L
from turtle import pd
from utils import gpt3, propose_decomposition, propose_instruction, chunks, get_subset, OpenAIModel, cache_dir

import datasets
import numpy as np
from tqdm import tqdm
import json, pdb
import re


data = datasets.load_dataset('gsm8k', 'main', cache_dir=cache_dir)['test']
inputs = [d['question'] for d in data][:500]
labels = [d['answer'].split('#### ')[-1] for d in data][:500]

io_pairs = [("""Mason is cleaning out all the junk in his attic. 20%% of the items are useful, 10%% are valuable heirlooms, and 70%% are junk. If Marcus's attic has 8 useful items in it, how many junk items does it have?""",
"28"),
("""A gecko eats 70 crickets every three days.  The first day she eats 30%% of the crickets.  The second day she eats 6 less than the first, and the third day she finishes up the remaining crickets.  How many crickets does she eat on the third day?""",
"34"),
("""My new house has 12 medium ceiling lights but I have seen small and large ceiling lights in other rooms. The small ones require 1 bulb, the medium ones require 2, and the large ones need 3 bulbs. How many bulbs should I buy if my wife says she saw twice as many large ceiling lights as medium ceiling lights and ten more small lights than medium ones?""",
"118"),
("""Tim buys a cabinet for $1200 and gets a 15%% discount.  How much did he pay?"""
"1020"),
("""Grant scored 10 points higher on his math test than John.  John received twice as many points as Hunter who scored a 45 on his math test.  What was Grant's test score?"""
"100"),
]

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


def gsm8k():
    def predict(chunk):
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=200, quote='---', n=1)
        prompts = ["""Mason is cleaning out all the junk in his attic. 20%% of the items are useful, 10%% are valuable heirlooms, and 70%% are junk. If Marcus's attic has 8 useful items in it, how many junk items does it have?
28
----
A gecko eats 70 crickets every three days.  The first day she eats 30%% of the crickets.  The second day she eats 6 less than the first, and the third day she finishes up the remaining crickets.  How many crickets does she eat on the third day?
34
----
My new house has 12 medium ceiling lights but I have seen small and large ceiling lights in other rooms. The small ones require 1 bulb, the medium ones require 2, and the large ones need 3 bulbs. How many bulbs should I buy if my wife says she saw twice as many large ceiling lights as medium ceiling lights and ten more small lights than medium ones?
118
----
Tim buys a cabinet for $1200 and gets a 15%% discount.  How much did he pay?
1020
----
Grant scored 10 points higher on his math test than John.  John received twice as many points as Hunter who scored a 45 on his math test.  What was Grant's test score?
100
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
        preds = [re.search("[0-9,.]+", p).group(0).replace(",", "") for p in preds]
        perf_array.append(exact_match(labels, preds))
    print("No decomposition Performance:")
    print("Mean", np.mean(perf_array))
    print("Std. Dev", np.std(perf_array))

def auto_cot(temperature=0.3):
    auto_cot_prompt = ""
    for io_pair in io_pairs[:5]:
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=1000, temperature=0.7, quote='---', n=1)
        prompt = """%s\n"""% task_description + io_pair[0] + \
            """\nThe final answer one of the five options.\nA: Let's think step-by-step.\n""" 
        auto_cot_prompt += prompt
        cot = gpt3(prompt)
        auto_cot_prompt += cot[0] + "\n----\n"
        # Add the final answer with special format so evaluation is easier.
    print(auto_cot_prompt)

    def predict(chunk):
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=500, temperature=temperature, quote='---', n=1)
        prompts=[auto_cot_prompt + """%s\n"""%task_description + \
            """%s\nThe final answer one of the five options.\nA: Let's think step-by-step.\n"""% (x) for x in chunk]
        return gpt3(prompts)

    perf_array = []
    runs = 20
    for run in range(runs): 
        print("Run %d"%run)
        answers = []
        label_dict = ["ABCDE".index(l) for l in labels]
        pdb.set_trace()
        new_labels = [re.split('[ABCDE]\)', inp[re.search("A\)", inp).span(0)[0]:])[1:][label_dict[i]] for i, inp in enumerate(inputs)]
        for x in tqdm(chunks(inputs, 20)):
            # x = [ex.replace("\nA:", "") for ex in x]
            answers.extend(predict(x))
            pdb.set_trace()
        preds = [x.strip() for x in answers]
        perf_array.append(substring_match(new_labels, preds))
    print("Auto-CoT Performance:")
    print("Perf Array", perf_array)
    print("Mean", np.mean(perf_array))
    print("Std. Dev", np.std(perf_array))


auto_cot(temperature=0.3)