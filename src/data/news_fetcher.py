import requests

def fetch_stock_news(symbol):

    url = f"https://newsapi.org/v2/everything?q={symbol}&apiKey=YOUR_KEY"

    response = requests.get(url).json()

    headlines = []

    for article in response["articles"][:10]:
        headlines.append(article["title"])

    return headlines