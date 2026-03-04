with open('test_examples_snapshot.py', 'r') as f:
    content = f.read()

content = content.replace('pbp_example_3_draft.json', 'examples/gameday_snapshot.json')
content = content.replace('0.40', '0.43')
content = content.replace('0.07', '0.075')

with open('test_examples_snapshot.py', 'w') as f:
    f.write(content)
