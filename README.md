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
│   ├── __pycache__.py
│   ├── logos                                # File with all logos used in charts and app
│   ├── data_preparation.py                  # Full data scraping & cleaning pipeline
├── app.py                                   # Interactive application with various statistics and comparisons
├── Final_analysis.ipynb                     # Main notebook (run this)
├── README.md
└── requirements.txt
```

## Data Sources & Features

The project automatically scrapes and processes **NHL match level data (2008–2025):** with all variables.
Further, it contains a folder of **Logos of all teams**.

Key engineered features include:

- preparation of the final variables 
- a visualised impact of the key variables on match results
- comparison of the impact within different situations
- an app for interactive visualizations of the impacts

## How to Run the Project

**Important:** Users should only execute code inside **`Final_report.ipynb`** and **`Final_report.ipynb`**.

**Python Version:** This project was developed and tested using **Python 3.9.6.** Using a significantly older or newer version may lead to dependency conflicts.

All scraping, cleaning, modeling, and visualization steps are **orchestrated from the notebook and the app**.
The Python modules in `data_preparation/` are imported internally and are **not intended to be run directly**.

### Steps

1. Clone the repository  
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Open and run **`Final_analysis.ipynb`** from top to bottom and the **`app.py`**

No additional scripts need to be executed manually.

## Data Pipeline

The data pipeline is implemented across the modules in `data_preparation/` and is triggered
from the notebook:

1. Scrape raw data from multiple online sources  
2. Clean and normalize team data  
3. Correct known historical inconsistencies (e.g. number of teams)  
4. Merge datasets into a unified analytical table  
5. Compute and visualize the impact 

## Dependencies

Key libraries used in this project include:

- pandas, numpy  
- matplotlib, seaborn  
- scikit-learn, scipy  
- requests, beautifulsoup4
- cairosvg

## Notes

- Web scraping depends on external websites and may break if page structures change  
- Scraping should be used responsibly and sparingly  
- Some cleaning steps are intentionally conservative to preserve historical consistency  

## License

This project is intended for **educational and research purposes**.
