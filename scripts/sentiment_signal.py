def sentiment_signal(score):

    if score["returns"] > 0 and score["sentiment_score"] > 0.2:
        signal = 1

    elif score["returns"] < 0 and score["sentiment_score"] < -0.2:
        signal = -1

    else:
        signal = 0