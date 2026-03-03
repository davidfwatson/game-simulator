import json

def main():
    with open('pbp_example_3_draft.json', 'r') as f:
        data = json.load(f)
    print("Pitch count:")
    events = data['liveData']['plays']['allPlays'][0]['playEvents']
    print(events)

if __name__ == '__main__':
    main()
