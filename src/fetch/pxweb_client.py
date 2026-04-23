"""Generic PxWeb API client with POST-based JSON query and automatic chunking.

Provides a low-level function that sends a PxWeb JSON query to any SCB table
endpoint and returns a pandas DataFrame.  Handles the 30 000-cell limit by
splitting large queries into chunks along the time dimension and concatenating
the results.
"""
