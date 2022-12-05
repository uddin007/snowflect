library(shiny)
library(DT)
library(ggplot2)
library(lubridate)
library(DBI)
library(odbc)
library(dplyr)
library(wordcloud)
library(RColorBrewer)
library(plotly)

fluidPage(
  tags$head(
    tags$style(HTML("
                    .navbar .navbar-nav {float: right}
                    "))
  ),
  tags$style(type="text/css",
             ".shiny-output-error { visibility: hidden; }",
             ".shiny-output-error:before { visibility: hidden; }"
  ),
  navbarPage(title = img(src="Logomakr_76tdkB.png", height = 22, width = 22),
             inverse = TRUE,
             collapsible = TRUE,
             windowTitle = "socialNet",
             
             tabPanel("reddit",
                      fluidRow(
                        column(6,
                               h4("Select Start Date"),
                               uiOutput("startTime"),
                               hr()
                        ),
                        column(6,
                               h4("Select Stock"),
                               uiOutput("uniqueStocks"),
                               hr()
                        ),
                        column(4, align="center",
                               h4("Most Frequest Stocks"),
                               plotOutput("wordCloud")
                        ),
                        column(4, align="center",
                               h4("Historical Stock Submission"),
                               plotlyOutput("stockHist")
                        ),
                        column(4, align="center",
                               h4("Historical Stock Sentiment"),
                               plotlyOutput("stockSent")
                        ),
                        column(12, align="center",
                               hr(),
                               h4("Stock Submission Count"),
                               dataTableOutput("head"),
                               hr()
                        ),
                        column(3,
                               h5("© 2021 snowflect.com")
                        ),
                        column(3,
                               tags$a(href="mailto:graupel007@gmail.com", h5("Contact"))
                        ),
                        column(6, align = "right",
                               tags$a(href="https://www.linkedin.com/shareArticle?mini=true&url=http%3A//plotstat.com/mlearn/&title=&summary=&source=", class = "fa fa-linkedin", target="_blank"),
                               tags$a(href="https://twitter.com/home?status=http%3A//plotstat.com/mlearn/", class = "fa fa-twitter", target="_blank"),
                               tags$a(href="https://www.facebook.com/sharer/sharer.php?u=http%3A//plotstat.com/mlearn/", class = "fa fa-facebook", target="_blank"),
                               tags$a(href="https://plus.google.com/share?url=http%3A//plotstat.com/mlearn/", class = "fa fa-google-plus", target="_blank"),
                               tags$a(href="https://www.reddit.com/login?dest=http://plotstat.com/mlearn/", class = "fa fa-reddit", target="_blank"),
                               tags$a(href="https://pinterest.com/pin/create/button/?url=http%3A//plotstat.com/mlearn/&media=&description=", class = "fa fa-pinterest", target="_blank"),
                               icon(NULL, class = "text/css", lib = "font-awesome"),
                               tags$style(type='text/css', ".fa {padding: 5px;font-size: 25px;}")
                               
                               #tags$style(type='text/css', ".fa {padding: 20px;font-size: 30px;width: 50px;text-align: center;text-decoration: none; border-radius: 50%;}")
                        )
                      ) # fluidrow ends 
             ) # data tabpanel ends
  ) # navbar page ends
) # fluid page ends