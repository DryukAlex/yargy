# coding: utf-8
import re

from plyplus import Grammar, STransformer
from pymorphy2 import MorphAnalyzer


class TokenTransformer(STransformer):

    def __init__(self):
        self.morph = MorphAnalyzer()

    def word(self, node):
        node.value = node.tail[0]
        node.pos = set()
        node.grammemes = set()
        node.forms = set()
        for form in self.morph.parse(node.value):
            node.pos = node.pos | {form.tag.POS}
            node.grammemes = node.grammemes | set(form.tag.grammemes)
            node.forms = node.forms | {form.normal_form}
        return node

    def int(self, node):
        node.value = int(node.tail[0])
        return node

    def float(self, node):
        node.value = float(node.tail[0])
        return node

class FactParser(object):

    def __init__(self, rules):
        self.rules = rules
        self.text_grammar = TEXT_GRAMMAR
        self.text_cleaning_regex = TEXT_CLEANING_REGEX
        self.text_transformer = TEXT_TRANSFORMER

    def parse(self, text):
        text = self.text_cleaning_regex.sub(" ", text)
        ast = self.text_grammar.parse(text)
        tokens = self.text_transformer.transform(ast)
        return self.extract(tokens, self.rules)

    def extract(self, tokens, rules):
        stack = []
        rule_index = 0
        while len(tokens.tail):
            token = tokens.tail.pop(0)
            rule_type, rule_options = rules[rule_index]
            rule_labels = rule_options.get("labels", [])
            rule_repeat = rule_options.get("repeat", [])
            if rule_type == "$":
                yield stack
                stack = []
                rule_index = 0
            elif token.head == rule_type:
                if all(self.check_labels(token, rule_labels, stack)):
                    stack.append(token)
                    if not rule_repeat:
                        rule_index += 1
                else:
                    if rule_repeat:
                        tokens.tail.insert(0, token)
                        rule_index += 1
                    else:
                        stack = []
                        rule_index = 0
            else:
                if rule_repeat:
                    tokens.tail.insert(0, token)
                    rule_index += 1
                else:
                    stack = []
                    rule_index = 0
        else:
            if stack and rule_index == len(rules) - 1:
                yield stack

    def check_labels(self, token, labels, stack):
        for label in labels:
            for name, value in label.items():
                yield LABELS_LOOKUP_MAP[name](token, value, stack)

TEXT_GRAMMAR = Grammar(r"""
    start: (word | float | int | dot | comma | quote)?* ;
    word: '[\w]+' | '[\w+\-]*[\w]+' ;
    int: '[+-]?[\d]+' ; 
    float: '[+-]?[\d]+[\.][\d]+' ; 
    dot: '\.' ; 
    comma: ',' ; 
    quote: '[\"\'«»`]' ; 
    SPACES: '[ \n\r\t]+' (%ignore) ;
""")
TEXT_CLEANING_REGEX = re.compile(r'[^\w\d\s\-\n\.\"\'«»`,]', flags=re.M | re.U | re.I)
TEXT_TRANSFORMER = TokenTransformer()


def gram_label(token, value, stack):
    return value in token.grammemes

LABELS_LOOKUP_MAP = {
    "gram": gram_label,
}