import pandas as pd

american_df = pd.read_csv('american_fork_chiropractors.csv')
spanish_df = pd.read_csv('spanish_fork_chiropractors.csv')

combined_df = american_df.append(spanish_df, sort=False)
combined_df.to_csv("american_spanish_chiropractor.csv")
