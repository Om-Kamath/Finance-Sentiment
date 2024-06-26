import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import streamviz
import requests

API_URL_SENTIMENT = "https://flowise.codesm.xyz/api/v1/prediction/2702a14a-10b7-4bba-b7a4-aad5ddef2647"
API_URL_INSIGHTS = "https://flowise.codesm.xyz/api/v1/prediction/5923f507-b119-401a-9e0c-65a53e6666bf"
headers = {"Authorization": f"Bearer {st.secrets['FLOWISE']}"}


df = pd.read_csv('us_symbols.csv')

st.markdown("""
            <style>
            .stPlotlyChart {
                height:275px !important;
            """, unsafe_allow_html=True)

sentiment_scores = {
    "Very Positive": 2,
    "Positive": 1,
    "Neutral": 0,
    "Negative": -1,
    "Very Negative": -2
}

def get_key_insights(news_summary, final_score):
    # fetch only summary and sentiment
    insights = []
    for news in news_summary:
        insights.append({
            'summary': news['summary'],
            'sentiment': news['sentiment']
        })
    payload = {
        'question': f"Final Score:{final_score},{insights}",
    }
    response = requests.post(API_URL_INSIGHTS, json=payload, headers=headers)
    key_insights = response.json()['text']
    return key_insights

def get_feed_summary(ticker, stock):
    url = f'https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US'
    feed = feedparser.parse(url)
    news_summary = []
    for news in feed['entries']:
        if stock.split()[0].lower() in news['title'].lower():
            payload = {
                'question': f"Stock:{stock}, Title:{news['title']}, Summary:{news.get('summary', 'No summary available')}",
            }
            response = requests.post(API_URL_SENTIMENT, json=payload, headers=headers)
            sentiment = response.json()['text']
            print(sentiment)
            filtered_news = {
                'title': news['title'],
                'link': news['link'],
                'summary': news.get('summary', 'No summary available'),
                'published': news.get('published', 'No publish date available'),
                'sentiment': sentiment if sentiment else 'No sentiment available'
            }
            news_summary.append(filtered_news)
    return news_summary


def main():
    st.title('Sentiment Analysis')
    stock = st.selectbox('Enter the stock name: ', df['name'].unique(), index=None)
    if stock:
        ticker = df[df['name'] == stock]['ticker'].values[0]
        data = yf.Ticker(ticker)
        st.markdown(f"## [{data.info['shortName']}]({data.info['website']})")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                    label="Stock Price",
                    value="%.2f" % data.info["currentPrice"],
                    delta="%.2f" % (data.info["currentPrice"] - data.info["previousClose"]),
                )
        with col2:
            st.metric(label="Today's High", value="%.2f" % data.info["dayHigh"])
        with col3:
            st.metric(label="Today's Low", value="%.2f" % data.info["dayLow"])

        with st.expander("Company Description"):
            st.write(data.info['longBusinessSummary'])

        with st.spinner('Analyzing Market Mood...'):
            total_sentiment_score = 0
            news_summary = get_feed_summary(ticker, stock)
            
            # Calculate total sentiment score first
            for news in news_summary:
                sentiment = news.get('sentiment', 'Neutral')  # Default to 'Neutral' if not present
                if sentiment in sentiment_scores:
                    score = sentiment_scores[sentiment]
                    total_sentiment_score += score
            
            # Normalize the score
            max_possible_score = len(news_summary) * 2 
            min_possible_score = len(news_summary) * -2  
            normalized_score = (total_sentiment_score - min_possible_score) / (max_possible_score - min_possible_score)
            final_score = normalized_score * 1  # Adjusted to scale 0-5 as per previous discussion
            final_score = max(0, min(final_score, 1))
            
            # Display the gauge before the news summaries
            streamviz.gauge(
                final_score, 
                gTitle="Market Mood Index", 
                gMode="number+gauge", 
                gSize="MED", 
                sFix=None,
                gcLow="#FF1708", 
                gcMid="#FF9400", 
                gcHigh="#1B8720"
            )
            key_insights = get_key_insights(news_summary, final_score).replace('$','\$')
            st.markdown(f"### Key Insights")
            st.markdown(key_insights)
            st.markdown(f"### Articles related to {stock}")
            # Then display each news summary
            for news in news_summary:
                st.markdown(f"#### [{news['title']}]({news['link']})")
                st.markdown(f":blue-background[Published on {news['published']}]")
                st.write(news['summary'].replace('$','\$'))
                sentiment = news.get('sentiment', 'Neutral')  # Default to 'Neutral' if not present
                if sentiment in sentiment_scores:
                    print(sentiment)
                    score = sentiment_scores[sentiment]
                    color = "green" if score > 0 else "red" if score < 0 else "orange"
                    st.markdown(f":{color}-background[{sentiment}]")
                else:
                    st.markdown(f":orange-background[Unknown Sentiment]")
                st.divider()
main()