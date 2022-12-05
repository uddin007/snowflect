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

Sys.setenv(TZ = "America/New_York")

function(input, output, session) {
  
  # Assign System Date ###############################################################################################################################  
  
  #isolate(values$day <- Sys.Date())
  
  output$startTime <- renderUI({ dateInput("sDate", "Start Date", value = "2021-07-23") })
  
  # Reddit Data #######################################################################################################################################  
  
  con <- DBI::dbConnect(odbc::odbc(),
                        Driver    = "FreeTDS", #"ODBC Driver 17 for SQL Server", 
                        Server    = "dbsanalytics2021.database.windows.net",
                        Database  = "db_social_media_2021",
                        UID       = "suddin",
                        PWD       = "Friendsnew3",
                        Port      = 1433,
                        TDS_Version = 7.4)
  
  redditData <- reactive({
    
    dbGetQuery(con, paste0(" SELECT * FROM redditPostCount WHERE RunDate >= '",input$sDate,"' "))
    
  })
  
  stockSentData <- reactive({
    
    dbGetQuery(con, paste0(" SELECT * FROM sentimentStock WHERE ticker = '",input$stockSymb,"' "))
    
  })
  
  parseData <- reactive({
    
    redditData() %>% group_by(Symbol,Name,Exchange) %>% summarise(submissionCount = sum(Count)) %>% arrange(desc(submissionCount))
    
  })
  
  ### Table Output
  output$head <- renderDataTable({parseData()})
  
  ### Point graph inputs 
  output$uniqueStocks <- renderUI({selectizeInput('stockSymb', 'Stock', as.list(unique(redditData()[,"Symbol"])), selected = "AMC", multiple = FALSE)})
  
  ### Point graph
  # Historical submission 
  output$stockHist <- renderPlotly({
    
    # Change data type
    df <- redditData()
    df$Count <- as.numeric(df$Count)
    df$RunDate <- ymd_hms(df$RunDate)
    
    # Create Basic Plot
    # hp <- ggplot(subset(df, Symbol == input$stockSymb), aes(x=RunDate,y=Count)) + geom_line()
    
    hp <- plot_ly(subset(df, Symbol == input$stockSymb), x = ~RunDate, y = ~Count, type = 'scatter', mode = 'markers')
    
    # Print plot
    print(hp)
    
  })
  
  ### Point graph
  # Historical sentiment 
  output$stockSent <- renderPlotly({
    
    # Load data/ change type if necessary 
    df <- stockSentData()
    
    # Create Basic Plot
    hp <- plot_ly(df, x = ~newsdate, y = ~compound, type = 'scatter', mode = 'markers')
    
    # Print plot
    print(hp)
    
  })
  
  ### Word cloud
  # Most frequent word list 
  output$wordCloud <- renderPlot({
    
    # Change data type
    df <- parseData()
    df$submissionCount <- as.numeric(df$submissionCount)
    
    # Create Basic Plot
    set.seed(1234)
    hp <- wordcloud(words = df$Symbol, freq = df$submissionCount, min.freq = 1, max.words=100, random.order=FALSE, rot.per=0.35, 
                    scale=c(8,1), colors=brewer.pal(8, "Dark2"))
    
    # Print plot
    print(hp)
    
  })
  
}