
# ---------- Load Data ------------------
data <- read.csv("all_interarrivals_new_features.csv")
head(data)
#data <- subset(data, data$DayofWeek == 'Monday')
#data <- subset(data, data$Interarrival < 500)
#data$Interarrival <- data$Interarrival*1000
print(nrow(data))
Interarrival = data$QtyShirt
#interarrival <- c(data$timestamp[1], diff(data$timestamp))
head(Interarrival)

# ---------- Exponential Distribution ------------------
expSample <- rexp(length(Interarrival))
qqplot(expSample, Interarrival)
qqline(Interarrival, distribution=qexp)

NLL <- function(lambda){
  likInterarrivals <- lambda * exp(-lambda * Interarrival)
  -sum(likInterarrivals, log=TRUE)
}

library(stats4)
maxLik <- mle(minuslogl = NLL, start=list(lambda=2))
summary(maxLik)

1/mean(Interarrival)

# ---------- Gamma Distribution ------------------
egamma(Interarrival, method = "mle", ci = FALSE, 
       ci.type = "two-sided", ci.method = "normal.approx", 
       normal.approx.transform = "kulkarni.powar", conf.level = 0.95)

eqgamma(Interarrival, p = 0.5, method = "mle", ci = FALSE, 
        ci.type = "two-sided", conf.level = 0.95, 
        normal.approx.transform = "kulkarni.powar", digits = 0)


# ---------- Weibull Distribution ------------------
eweibull(Interarrival, method = "mle")


# ---------- Data Filtering ------------------
data <- read.csv("all_interarrivals_new_features.csv")
head(data)
#data <- subset(data, data$DayofWeek == 'Monday')
#data <- subset(data, data$Hour_ofday == 0)
print(nrow(data))
Interarrival = data$QtyShirt #seconds
head(Interarrival)

#data_2 <- subset(data, data$DayofWeek == 'Sunday')
#Interarrival = replace(Interarrival,which(Interarrival==0),0.0001)
#Interarrival = sample(Interarrival, length(Interarrival)/4)
#Interarrival_scaled <- (Interarrival - min(Interarrival) + 0.001) / (max(Interarrival) - min(Interarrival) + 0.002)

# ---------- Multiple Distribution Comparisons ------------------
# Cullen & Fray Graph
library(fitdistrplus)  # on CRAN 
descdist(Interarrival, boot=1000)

# Build models to compare
gammafit  <-  fitdistrplus::fitdist(Interarrival, "gamma", lower=c(0,0), start=list(scale=1,shape=1))
summary(gammafit)

weibullfit  <-  fitdistrplus::fitdist(Interarrival, "weibull")
summary(weibullfit)

lnormfit  <-  fitdistrplus::fitdist(Interarrival, "lnorm")  # not supported?
summary(lnormfit)

expofit  <-  fitdistrplus::fitdist(Interarrival, "exp")
summary(expofit)

poisfit  <-  fitdistrplus::fitdist(Interarrival, "pois")
summary(poisfit)

library(flexsurv) # on CRAN
gengammafit  <-  fitdistrplus::fitdist(Interarrival_scaled, "gengamma", lower=c(0,0,0), 
                                       start=function(d) list(mu=mean(d),
                                                              sigma=sd(d),
                                                              Q=0))
summary(gengammafit)

# Compare QQ plots of all distributions
qqcomp(list(gammafit, weibullfit, lnormfit, expofit),
       legendtext=c("gamma", "weibull", "lnorm","expo") )

qqcomp(list(gammafit, expofit),
       legendtext=c("gamma","expo") )

qqcomp(expofit)

# If error in QQ plots - 
par("mar")
par(mar=c(1,1,1,1))

