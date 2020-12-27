# Predicting usefulness of reviews from review texts
## Abstract/Synopsis

To e-commerce (online shopping), reviews are as important to buyer as to sellers. Shoppers peruse pages of reviews to find relevant information before commiting to buy the products. Sellers did the same things to see what worked well and what did not go as expected. Good or positive reviews are probably the best marketing tactics that influence sales for less popular, well-known brand. Conversely, bad or negative reviews shoo potential customers away (probably to competitors). Thus it's not surprising that many emerging, private brands give customers nonsignificant rebates for writing reviews about product. 

As the maker of the biggest E-commerce platform, can Amazon use it data to spot out useful reviews from trivial ones? Without algorithms, a review would have to endure the test of time to see its place in the review sections. Without algorithms, a review appears on top may be a fake review that comes from a different version of product, or worse, from a completely different product. Mining review texts and rearranging them are supposed to benefit both consumers and sellers. For buyers, the time saved from filtering all the noise can be used to critically assess different product alternatives. For sellers, reviewing a much smaller dataset can reduce costs and time involved in the same activity.

## Outline

The following analysis explores the feasibility of spotting useful reviews from trivial ones. It also attempt to suggest an approach to apply it at scale and discuss potential limitations.

The analysis has two main parts:
1. Base and Train: this notebook outlines step by step from downloading the dataset to experiment with different parameters of Latent Dirichlet Allocation (LDA), visually and individually inspect the results. The goal is to establish a performance baseline on a reasonable small dataset
2. Extend and Validate: this notebook wrap all steps in a function so that it can be applied to different and bigger dataset to compare if performance changes as we extend the scale.

## Extra Resources
Latent Dirichlet Allocation:
https://cacm.acm.org/magazines/2012/4/147361-probabilistic-topic-models/fulltext
https://hbsp.harvard.edu/tu/5b4b3414
https://towardsdatascience.com/light-on-math-machine-learning-intuitive-guide-to-latent-dirichlet-allocation-437c81220158
https://medium.com/@pratikbarhate/latent-dirichlet-allocation-for-beginners-a-high-level-intuition-23f8a5cbad71
Jensen-Shannon Distance:
https://medium.com/datalab-log/measuring-the-statistical-similarity-between-two-samples-using-jensen-shannon-and-kullback-leibler-8d05af514b15

## References/Acknowledgement
Last but not least, I couldn't pull this project off without the detailed instructions from these articles:
https://kldavenport.com/topic-modeling-amazon-reviews/#querying-the-lda-model
https://towardsdatascience.com/topic-modelling-in-python-with-nltk-and-gensim-4ef03213cd21
https://www.kaggle.com/ktattan/lda-and-document-similarity
Also Google Colab and their generosity with hosting the datasets
