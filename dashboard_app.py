# -*- coding: utf-8 -*-
"""
Comment data fetched using https://chromewebstore.google.com/detail/youtube-comment-summary-w/mcooieiakpekmoicpgfjheoijfggdhng?hl=en
YouTube Channel info fetched using https://commentpicker.com/youtube-channel-id.php

"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from datetime import datetime
import seaborn as sns

from os import path
from PIL import Image
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator
import matplotlib.pyplot as plt

#import nltk
#nltk.download("vader_lexicon")
from nltk.sentiment import SentimentIntensityAnalyzer



def style_negative(v, props=''):
    """ Style negative values in dataframe"""
    # try-except is a way to get around the need to not color the text columns
    try:
        return props if v < 0 else None
    except:
        pass

def style_positive(v, props=''):
    """Style positive values in dataframe"""
    try:
        return props if v > 0 else None
    except:
        pass


#@st.cache_data
def load_data():
    yt_data = pd.read_csv("data/serpadesign_yt_scraped_data.tsv", sep="\t", parse_dates=["Published"])
    yt_data.drop(labels=["Source", "Location Name", "Location", "Audio Language", "Unnamed: 0", "data_id", "Projection",
                         "License", "Dimension", "Embeddable", "Licensed Content", "Definition", "Caption",
                         "Privacy Status", "Localization Count"],
                 axis=1, inplace=True)
    yt_data.dropna(axis=1, how="all", inplace=True)

    yt_data["Views"] = pd.to_numeric(yt_data["Views"].str.replace(",", ""))
    yt_data["Comments"] = pd.to_numeric(yt_data["Comments"].str.replace(",", ""))
    yt_data["Likes"] = pd.to_numeric(yt_data["Likes"].str.replace(",", ""))
    yt_data.set_index("Published", inplace=True, drop=False)
    yt_data["Date"] = yt_data['Published'].dt.strftime("%Y-%m-%d")

    # feature eng
    #yt_data["Engagement"] = (yt_data["Comments"]+yt_data["Likes"])/yt_data["Views"]
    yt_data["Engagement"] = (yt_data["Comments"]) / yt_data["Views"]

    # Add channel info
    channel_info_data = pd.read_csv("data/youtube-channel.csv")

    # Add some comments data - Ugly data import
    from data.comments import comments

    # Add sentiment data
    #  The negative, neutral, and positive scores are related: They all add up to 1 and can’t be negative. The compound score is calculated differently. It’s not just an average, and it can range from -1 to 1.

    sia = SentimentIntensityAnalyzer()
    for k, v in comments.items():
        v['Sentiment'] = v['comment'].apply(lambda c: sia.polarity_scores(c)["compound"])

    return yt_data, channel_info_data, comments


# create dataframes from the function
yt_data, channel_info_data, comments = load_data()
ave_sentiment_global = np.mean([v["Sentiment"].mean() for k,v in comments.items()])

yt_data["Views Difference"] = yt_data["Views"] - yt_data["Views"].mean()
yt_data["Comments Difference"] = yt_data["Comments"] - yt_data["Comments"].mean()
yt_data["Likes Difference"] = yt_data["Likes"] - yt_data["Likes"].mean()
yt_data["Engagement Difference"] = yt_data["Engagement"] - yt_data["Engagement"].mean()

# app - dashboard
add_sidebar = st.sidebar.selectbox('Select view', ('Profile', 'Aggregate analysis', "Comments sentiment analysis"))


if add_sidebar == "Profile":
    st.markdown("# Dashboard for SerpaDesign YouTube channel")

    # Tag Wordcloud
    wordcloud_text = (", ").join(yt_data.Tags.apply(str))
    wordcloud = WordCloud(background_color = 'white',
                    width = 512,
                    height = 384).generate(wordcloud_text)
    # Display the generated image:
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    st.pyplot(plt)

    col1, col2, col3 = st.columns(3)
    columns = [col1, col2, col3]

    for e, metric in enumerate(["Subscriber count", "View count", "Video count"]):
        with columns[e % 3]:
            st.metric(metric, channel_info_data[metric])


elif add_sidebar == "Aggregate analysis":
    # Metrics
    metrics = []
    df_agg_metrics = yt_data[['Published', 'Views', 'Likes', 'Comments', 'Engagement',
                              "Views Difference", "Comments Difference", "Likes Difference", "Engagement Difference",
                              # 'Subscribers','Shares','RPM(USD)','Average % viewed',
                              #          'Avg_duration_sec', 'Engagement_ratio','Views / sub gained'
                              ]]
    metric_date_6mo = df_agg_metrics['Published'].max() - pd.DateOffset(months=6)
    metric_date_12mo = df_agg_metrics['Published'].max() - pd.DateOffset(months=12)
    metric_medians6mo = df_agg_metrics[df_agg_metrics['Published'] >= metric_date_6mo].median()
    metric_medians12mo = df_agg_metrics[df_agg_metrics['Published'] >= metric_date_12mo].median()

    # TODO Add Dummy made up metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    columns = [col1, col2, col3, col4, col5]

    for e, i in enumerate(metric_medians12mo.index.drop(["Published"])):
        with columns[e % 5]:
            delta = (metric_medians6mo[i] - metric_medians12mo[i]) / metric_medians12mo[i]
            metrics.append(( i, metric_medians6mo[i], "{:.2%}".format(delta) ))
            metric_value = round(metric_medians6mo[i])
            if i == "Engagement":
                #metric_value = "{:.2%}".format(metric_value)
                metric_value = "N/A"
            st.metric(label=i, value=metric_value, delta="{:.2%}".format(delta), help="Metrics over last 6 months and percentage change relative to last 12 months") # label, value, delta, tooltip_text

    from plotly.subplots import make_subplots
    fig_time_series = make_subplots(rows=4, cols=1, vertical_spacing = 0.05, shared_xaxes=True)
    for e,v in enumerate(["Views", "Comments", "Likes", "Engagement"]):
        fig_time_series.add_trace(
                go.Scatter(x=yt_data.index, y= yt_data[v], mode="lines", name=v),
            row=e+1, col=1)

    fig_time_series.update_traces(hovertemplate=None)
    fig_time_series.update_layout(hovermode="x unified")
    fig_time_series.update_traces(xaxis='x1')
    st.plotly_chart(fig_time_series)

    st.dataframe(
        yt_data[["Date", 'Title', 'Views', 'Likes', 'Comments', 'Engagement', 'Length', "Views Difference", "Comments Difference", "Likes Difference", "Engagement Difference", "Description"]]\
            .set_index("Title")\
            #.sort_values("Date")\
            .style.hide()
            .applymap(style_negative, props='color:red;')\
            .applymap(style_positive, props='color:green;')
    )
    st.caption("Note: Aggregated data range: June 22nd 2013 - Sep 26th 2024")

# TODO Add data for all comments
if add_sidebar == "Comments sentiment analysis":
    videos_ids = comments.keys()
    videos_titles = yt_data[yt_data["Video ID"].isin(videos_ids)]["Title"].values
    selected_title = st.selectbox('Pick A Video', tuple(videos_titles)) #tuple(yt_data["Title"]))
    selected_id = yt_data[yt_data["Title"] == selected_title]["Video ID"].iloc[0]
    video_comment_data = comments[selected_id]

    # st.metric(label="Ave Sentiment", value="{:.2}".format(video_comment_data["Sentiment"].mean()), delta=video_comment_data["Sentiment"].mean()-ave_sentiment_global, help="Difference between average sentiment for this video and average sentiment for all videos")
    st.metric(label="Ave Sentiment", value="{:.2}".format(video_comment_data["Sentiment"].mean()), delta= "{:.2%}".format(video_comment_data["Sentiment"].mean()-ave_sentiment_global), help="Difference between average sentiment for this video and average sentiment for all videos")


    st.dataframe(video_comment_data, hide_index=True)
    st.caption("Note: Sentiment analysis uses very limited comment data.")
