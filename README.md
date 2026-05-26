# Impact of Individual Hockey Statistics on Game Results, and Goals Scored - Power Play & 5v5 Comprehension

**Authors:** Antonín Ježek & Tomáš Trnka

## Project Overview

This project examines the **impact** of different hockey statistics **on game results, and goals scored** in two situations. The situations for comprehension are **5v4** and **5v5**. The final variables for the regression are: **Face-Offs Won Percentage**, **Shots**, **Shots on goal**, **Home or Away**, and **Giveaways**.

Using historical **NHL data** from the season **2008/2009** to the season **2024/2025**, the project combines:

- data scraping
- data cleaning and processing  
- exploratory analysis and visualization
- regression on game results and goals scored

## Repository Structure

```
├── data_preparation/
│   ├── scraping/
│   │   ├── __init__.py
│   │   ├── scraping_all_teams.py       # NHL match level data scraper
│   │   ├── scraping_logos.py           # Team logo scraper (visualizations)
│   ├── Data_cleaning.py                  # Full data scraping & cleaning pipeline
├── Final_report.ipynb                    # Main notebook (run this)
├── README.md
└── requirements.txt
```

## Data Sources & Features

