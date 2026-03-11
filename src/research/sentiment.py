from textblob import TextBlob

def analyze_sentiment(text):
    return TextBlob(text).sentiment.polarity


def sentiment_from_news(news_list):

    scores = []

    for headline in news_list:
        scores.append(analyze_sentiment(headline))

    if len(scores) == 0:
        return 0

    return sum(scores) / len(scores)