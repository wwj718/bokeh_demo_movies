from os.path import dirname, join
import numpy as np
import pandas.io.sql as psql
import sqlite3 as sql

from bokeh.plotting import Figure
from bokeh.models import ColumnDataSource, HoverTool, HBox, VBoxForm
from bokeh.models.widgets import Slider, Select, TextInput
from bokeh.io import curdoc
from bokeh.sampledata.movies_data import movie_path  # /Users/wwj/.bokeh/data/movies.db,13M

conn = sql.connect(movie_path)
query = open(join(dirname(__file__), 'query.sql')).read()
movies = psql.read_sql(query, conn
                       )  #12569 rows × 26 columns , try  it in jupyter

#movies.columns: Index([u'ID', u'imdbID', u'Title', u'Year', u'mpaaRating', u'Runtime', u'Genre', u'Released', u'Director', u'Writer', u'Cast', u'imdbRating', u'imdbVotes', u'Language', u'Country', u'Oscars', u'numericRating', u'Meter', u'Reviews', u'Fresh', u'Rotten', u'userMeter', u'userRating', u'userReviews', u'BoxOffice', u'Production'], dtype='object')
'''
*  Oscars 奥斯卡
*  genre 体裁
*  BoxOffice 票房
*  采用了ast以至于开头无法添加 utf-8注释，只能使用字符串风格的注释，超过60%则是新鲜的，否则是烂的
*  Tomato Meter是一种评分标准，“烂番茄”
'''

# Oscars
movies["color"] = np.where(movies["Oscars"] > 0, "orange", "grey")
movies["alpha"] = np.where(movies["Oscars"] > 0, 0.9, 0.25)
movies.fillna(0, inplace=True)  # just replace missing values with zero
movies["revenue"] = movies.BoxOffice.apply(lambda x: '{:,d}'.format(int(x)))

with open(join(dirname(__file__), "razzies-clean.csv")) as f:
    razzies = f.read().splitlines()
movies.loc[movies.imdbID.isin(razzies), "color"] = "purple"
movies.loc[movies.imdbID.isin(razzies), "alpha"] = 0.9

axis_map = {
    u"烂番茄指标": "Meter",
    "Numeric Rating": "numericRating",
    u"评论数": "Reviews",
    u"票房(dollars)": "BoxOffice",
    "Length (minutes)": "Runtime",
    "Year": "Year",
}

# Create Input controls
reviews = Slider(title=u"最少评论数", value=80, start=10, end=300, step=10)
min_year = Slider(title=u"开始年份",
                  start=1940,
                  end=2014,
                  value=1970,
                  step=1)
max_year = Slider(title=u"结束年份",
                  start=1940,
                  end=2014,
                  value=2014,
                  step=1)
oscars = Slider(title=u"至少获得奥斯卡奖项", start=0, end=4, value=0, step=1)
boxoffice = Slider(title=u"票房 (millions)", start=0, end=800, value=0, step=1)
genre = Select(title=u"体裁",
               value="All",
               options=open(join(
                   dirname(__file__), 'genres.txt')).read().split())
director = TextInput(title=u"导演名字模糊搜索")
cast = TextInput(title=u"演员名字模糊搜索")
x_axis = Select(title=u"X 轴",
                options=sorted(axis_map.keys()),
                value=u"烂番茄指标")
y_axis = Select(title=u"Y 轴",
                options=sorted(axis_map.keys()),
                value=u"评论数")

# Create Column Data Source that will be used by the plot
'''用于绘图的参数'''
source = ColumnDataSource(data=dict(x=[],
                                    y=[],
                                    color=[],
                                    title=[],
                                    year=[],
                                    revenue=[]))
'''
点的悬停提示框
'''
hover = HoverTool(tooltips=[
    ("Title", "@title"), ("Year", "@year"), ("$", "@revenue")
])

p = Figure(plot_height=600,
           plot_width=800,
           title="",
           toolbar_location=None,
           tools=[hover])
p.circle(x="x",
         y="y",
         source=source,
         size=7,
         color="color",
         line_color=None,
         fill_alpha="alpha")


def select_movies():
    '''
    这是核心所在，使用用户的输入来筛选匹配的电影
    这里是起步的地方，最先应当构建这部分
    '''
    genre_val = genre.value
    director_val = director.value.strip()
    cast_val = cast.value.strip()
    selected = movies[
        (movies.Reviews >= reviews.value) & (movies.BoxOffice >= (
            boxoffice.value * 1e6)) & (movies.Year >= min_year.value) &
        (movies.Year <= max_year.value) & (movies.Oscars >= oscars.value)]
    if (genre_val != "All"):
        selected = selected[selected.Genre.str.contains(genre_val) == True]
    if (director_val != ""):
        selected = selected[selected.Director.str.contains(director_val) ==
                            True]
    if (cast_val != ""):
        selected = selected[selected.Cast.str.contains(cast_val) == True]
    return selected


def update(attrname, old, new):
    df = select_movies()
    x_name = axis_map[x_axis.value]
    y_name = axis_map[y_axis.value]

    p.xaxis.axis_label = x_axis.value
    p.yaxis.axis_label = y_axis.value
    p.title = "%d movies selected" % len(df)
    source.data = dict(x=df[x_name],
                       y=df[y_name],
                       color=df["color"],
                       title=df["Title"],
                       year=df["Year"],
                       revenue=df["revenue"],
                       alpha=df["alpha"], )


'''
这是所有的ui控件，这样一来pandas就可以可视化了，与用户交互
control.on_change 事件驱动
'''
controls = [reviews, boxoffice, genre, min_year, max_year, oscars, director,
            cast, x_axis, y_axis]
for control in controls:
    control.on_change('value', update)

inputs = HBox(VBoxForm(*controls), width=300)

update(None, None, None)  # initial load of the data

curdoc().add_root(HBox(inputs, p, width=1100))
