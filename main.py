import argparse
import subprocess
import numpy as np

from ast import parse, unparse, NodeTransformer, copy_location, Name, FunctionDef, Expr, Str


class NormIdentifiers(NodeTransformer):
    def __init__(self):
        self.identifiers = {}
        super().__init__()

    def visit_Name(self, node):
        try:
            id = self.identifiers[node.id]
        except KeyError:
            id = f'id_{len(self.identifiers)}'
            self.identifiers[node.id] = id

        return copy_location(Name(id=id), node)


class NormFunctions(NodeTransformer):
    def __init__(self, func=None):
        self.identifiers = {}
        self.func = func
        super().__init__()

    def visit_FunctionDef(self, node):
        if self.func and self.func != node.name:
            return None

        try:
            name = self.identifiers[node.name]
        except KeyError:
            name = f'function{len(self.identifiers):x}'
            self.identifiers[node.name] = name

        for i, arg in enumerate(node.args.args):
            arg.arg = f'arg{i}'

        new_func = FunctionDef(name=name, args=node.args, body=node.body, decorator_list=node.decorator_list)

        if isinstance(new_func.body[0], Expr) and isinstance(new_func.body[0].value, Str):
            del new_func.body[0]

        return copy_location(new_func, node)


def get_normed_content(filename):
    if filename.endswith('.py'):
        with open(filename) as src:
            content = src.read()
            try:
                tree = parse(content)
            except SyntaxError:
                print(f"Syntax error in {filename}. Comparing non-normalized source.")
                return filename, content

            tree = NormFunctions(func=None).visit(tree)
            tree = NormIdentifiers().visit(tree)

            return filename, unparse(tree)

    if filename.endswith('.c') or filename.endswith('.cpp'):
        asm = subprocess.check_output(['gcc', '-S', '-o-', filename])
        return filename, asm.decode('utf8')


# Levenshtein distance
def distance(token1, token2):
    distances = np.zeros((len(token1) + 1, len(token2) + 1))

    for t1 in range(len(token1) + 1):
        distances[t1][0] = t1

    for t2 in range(len(token2) + 1):
        distances[0][t2] = t2

    return distances[len(token1)][len(token2)]


def get_pair_stats(pair):
    dld = distance(pair[0][1], pair[1][1])
    avg_len = (len(pair[0][1]) + len(pair[1][1])) / 2.0
    percent = 100.0 * (1 - (dld / avg_len))
    return percent, dld, pair[0], pair[1]


def main():
    ap = argparse.ArgumentParser(description='Check source files for similarity')
    ap.add_argument('input', help="Text file with list of files to compare")
    ap.set_defaults(input='input.txt')
    ap.add_argument('output', help="Output file with list of result scores")
    ap.set_defaults(input='scores.txt')

    args = ap.parse_args()

    submissions = []
    with open(args.input, 'r') as input_file:
        for line in input_file:
            txt1, txt2 = line.split()
            submissions.append((get_normed_content(txt1), get_normed_content(txt2)))

    pairs = [get_pair_stats(pair) for pair in submissions]

    return_code = 0

    scores = []

    for sim, dld, a, b in pairs:
        print(f"{a[0]} and {b[0]}: similarity of {int(sim)}% with edit distance of {dld}\n")
        scores.append(sim)

        return_code = 1

        # if args.show_diff:
        #     print('\n'.join(difflib.ndiff(a[1].splitlines(), b[1].splitlines())))

    with open(args.output, "w") as output_file:
        output_file.write('\n'.join([str(round(fl, 2)) for fl in scores]))

    exit(return_code)


if __name__ == '__main__':
    main()
