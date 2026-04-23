"""Fetch municipal open unemployment rates from SCB STATIV table AA0003.

Downloads andel öppet arbetslösa (share of population 20–64 registered with
Arbetsförmedlingen) for all 290 kommuner for 2010–2024 using the generic
pxweb_client.  Caches raw response to data/raw/.  Returns a tidy DataFrame
with columns [kommun_kod, year, unemployment_rate].
"""
