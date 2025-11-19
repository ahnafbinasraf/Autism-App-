import pandas as pd
def load_preferred_modes():
    try:
        df = pd.read_csv('preferred_modes.csv')
        modes_dict = df.set_index('learner_id')['preferred_mode'].to_dict()
        
        # Only return the modes that exist in the CSV
        return modes_dict
    except Exception as e:
        print(f"Warning: Could not load preferred modes: {e}")
        # Return empty dict if CSV can't be loaded
        return {}

y = load_preferred_modes()
print(y)