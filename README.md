# Analyze assessments

This is built specifically to pilot an automated way of writing up
an assessment, given the tool created by Perry and Christian for 
gathering team member feedback. 

We hope that this will make it easy.

Picture this:
* Download the mural sticky notes as a CSV
* The script isolates the sticky notes as groups by team and topic
* We use Christian and Perry's color-based scoring
* We calculate the % positive and negative for feedback
* We report the topics of positive comments and negative comments
* Sentiment analysis recommends impactful statements (positive and negative)
* We produce scoring data for graphing (or graph it ourselves)
* The author imports the graphs, imports the quotes, and summarizes

This does not replace any human analysis, but it does automate
the mechanical work of tallying and sorting.

Directions:
* Produce a spreadsheet of the analytic results
* import the spreadsheet into a Google template for further work


# Prerequisites

To get your project ready to go with libraries and whatnot:
`poetry install`

We are using TextBlob in the project, and it has an extra one-time chore. 
You have to run:
`python -m textblob.download_corpora`

The other thing you need is to download the assessment mural as a PDF file.
Currently the filename is hard-coded in the script, but that's likely to 
change.

