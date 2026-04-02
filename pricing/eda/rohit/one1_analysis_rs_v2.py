# ---
# jupyter:
#   jupytext:
#     formats: py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.1
#   kernelspec:
#     display_name: Python 3 (ipykernel) (Local)
#     language: python
#     name: conda-base-py
# ---

# %%
# ------------------------------------------------------------
# STEP 1: LOAD DATA
# ------------------------------------------------------------

import pandas as pd
import numpy as np

url = "gs://agntworks-data-dev/sandbox/experiments/clean_flight_data_with_regime_v3.csv"

df = pd.read_csv(url, parse_dates=["dep_datetime"])

print("Shape:", df.shape)
df.head()

# %%
# Check for missing values across all columns
null_counts = df.isnull().sum()
null_percentages = (df.isnull().sum() / len(df)) * 100

# Combine into a summary table
data_quality_df = pd.DataFrame({
    'Null Count': null_counts,
    'Percentage (%)': null_percentages
}).sort_values(by='Null Count', ascending=False)

print("Data Quality Summary:")
print(data_quality_df[data_quality_df['Null Count'] > 0])

# Check for empty strings in the cluster columns specifically
print("\nEmpty string check for Clusters:")
print("Dep_cluster empties:", (df['Dep_cluster'] == '').sum())
print("Arr_cluster empties:", (df['Arr_cluster'] == '').sum())

# %%
unique_clusters = df['Dep_cluster'].unique()
print(unique_clusters)

# %%
# 1. Calculate the new 5% threshold
revenue_threshold_5pct = 0.05 * 155744323.30

# 2. Filter for clusters with 80+ flights AND >= 5% revenue
significant_clusters_df = cluster_stats[
    (cluster_stats['flight_count'] >= 80) & 
    (cluster_stats['total_rev'] >= revenue_threshold_5pct)
].sort_values(by='total_rev', ascending=False)

print(f"New 5% Revenue Threshold: ${revenue_threshold_5pct:,.2f}")
print("\n--- Significant 'Power Clusters' (5% Level) ---")
print(significant_clusters_df)

# Update your list for the next analysis step
significant_clusters = significant_clusters_df['Dep_cluster'].tolist()

# %%
