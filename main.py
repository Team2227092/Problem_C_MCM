import pandas as pd

import dataCleaner, regressionModels, wallet

import math

NUM_PROC = 4

def main():
    print("Starting...")

    dataCleaner.combineCSVs()

    global btcGoldDF
    btcGoldDF = pd.read_csv('./Data/finalData.csv')

    predictFuture()

def predictFuture():
    # TODO - find best starting day
    spikeTrader = {'Date': [], 'USD': [], 'Gold': [], 'BTC': [], 'Total Net Worth': []}
    spikeTrader['Date'].append('9/11/16')
    spikeTrader['USD'].append(1000)
    spikeTrader['Gold'].append(0)
    spikeTrader['BTC'].append(0)
    spikeTrader['Total Net Worth'].append(1000)
    myWallet = wallet.Wallet()
    startDay = 10

    while startDay < len(btcGoldDF):
        changes = False
        for product in ["BTC", "Gold"]:
            if (changes):
                break
            regressionModels.PREDICTION = product + ' Price'
            regressionModels.DATA = [product + 'DaysSinceRise', product + 'DaysSinceFall']
            predictionDF = pd.DataFrame(columns=['Price', 'Rise', 'Fall'])

            regressionModels.setRiseFallDays(startDay)
            model = regressionModels.gradientBoosting(startDay)
            for trainingDays in range(startDay+1, len(btcGoldDF)-1):
                predictionDict = {'Price': [], 'Rise': [], 'Fall': []}
                spike = False
                rise = 0
                fall = 0

                model = regressionModels.retrainModel(model, trainingDays)
                prediction = regressionModels.predictDay(model, trainingDays)

                regressionModels.addRiseFallDays(trainingDays, regressionModels.riseDays+1, regressionModels.fallDays+1)
                
                predictionDict["Price"] = prediction
                predictionDict["Rise"] = regressionModels.riseDays+1
                predictionDict["Fall"] = regressionModels.fallDays+1
                predictionDF = pd.concat([predictionDF, pd.DataFrame(predictionDict)])

                # TODO - check if rise or fall, distinguish which, get index of spike, break loop
                try:
                    value, index = findNextTopOfSpike(predictionDF["Price"], btcGoldDF[regressionModels.PREDICTION][startDay], myWallet.fees[product])
                    spike = True
                    rise += 1
                except:
                    pass
                try:
                    value, index = findNextBottomOfSpike(predictionDF["Price"], btcGoldDF[regressionModels.PREDICTION][startDay], myWallet.fees[product])
                    spike = True
                    fall += 1
                except:
                    pass

                if spike:
                    # TODO - buy or sell
                    availableMoney = myWallet.getAvailableMoney()
                    if (rise):
                        if (myWallet.wallet[product] > 0):
                            actualPrice = btcGoldDF.iloc[startDay + index][product + " Price"]
                            print("Selling " + str(myWallet.wallet[product]) + " " + product)
                            myWallet.sell(product, actualPrice)
                            startDay += index+1
                            changes = True
                            spikeTrader['Date'].append(btcGoldDF['Date'][startDay])
                            spikeTrader['USD'].append(myWallet.getAvailableMoney())
                            spikeTrader['Gold'].append(myWallet.getGoldAmount())
                            spikeTrader['BTC'].append(myWallet.getBTCAmount())
                            spikeTrader['Total Net Worth'].append(myWallet.getNetWorth(btcGoldDF['BTC Price'][startDay], btcGoldDF['Gold Price'][startDay]))
                            break
                    if (fall):
                        actualPrice = btcGoldDF.iloc[startDay + index][product + " Price"]
                        numberOfProducts = (math.floor(availableMoney / actualPrice))
                        newPrice = (actualPrice*numberOfProducts)
                        if newPrice+(newPrice*myWallet.fees[product]) > availableMoney:
                            numberOfProducts -= 1
                        if numberOfProducts <= 0:
                            continue
                        print("Buying " + str(numberOfProducts) + " " + product)
                        myWallet.buy(product, actualPrice, numberOfProducts)
                        startDay += index+1
                        changes = True
                        spikeTrader['Date'].append(btcGoldDF['Date'][startDay])
                        spikeTrader['USD'].append(myWallet.getAvailableMoney())
                        spikeTrader['Gold'].append(myWallet.getGoldAmount())
                        spikeTrader['BTC'].append(myWallet.getBTCAmount())
                        spikeTrader['Total Net Worth'].append(myWallet.getNetWorth(btcGoldDF['BTC Price'][startDay], btcGoldDF['Gold Price'][startDay]))
                        break

        if (not changes):
            startDay += 1

    for product in ["BTC", "Gold"]:
        if (myWallet.wallet[product] > 0):
            actualPrice = btcGoldDF.iloc[len(btcGoldDF)-1][product + " Price"]
            print("Selling " + str(myWallet.wallet[product]) + " " + product)
            myWallet.sell(product, actualPrice)
            spikeTrader['Date'].append('9/10/21')
            spikeTrader['USD'].append(myWallet.getAvailableMoney())
            spikeTrader['Gold'].append(myWallet.getGoldAmount())
            spikeTrader['BTC'].append(myWallet.getBTCAmount())
            spikeTrader['Total Net Worth'].append(myWallet.getNetWorth(0, 0))

    print(myWallet.wallet)
    
    spikeTraderDF = pd.DataFrame(spikeTrader)
    spikeTraderDF.to_csv('./Data/SpikeTraderGBx2.csv')

def getRiseFall(previousPrice, currentPrice):
    if previousPrice > currentPrice:
        return "Fell"
    elif previousPrice < currentPrice:
        return "Rose"
    else:
        return "Stayed" 

def predictPurchase(df, day):
    btc_transactionFee = 0.02
    gold_transactionFee = 0.01
    lastTrainingDayPrice = df[day]
    btc_prediction = regressionModels.MLPNN(day, 'BTC Price')
    gold_prediction = regressionModels.MLPNN(day, 'Gold Price')

    btc_bestNextBestValue = findNextTopOfSpike(btc_prediction, lastTrainingDayPrice, btc_transactionFee)    
    btc_bestNextWorstValue = findNextBottomOfSpike(btc_prediction, lastTrainingDayPrice, btc_transactionFee)

    gold_bestNextBestValue = findNextTopOfSpike(gold_prediction, lastTrainingDayPrice, gold_transactionFee)    
    gold_bestNextWorstValue = findNextBottomOfSpike(gold_prediction, lastTrainingDayPrice, gold_transactionFee)

    btc_gains = (lastTrainingDayPrice - btc_bestNextBestValue)
    gold_gains = (lastTrainingDayPrice - gold_bestNextBestValue)

    btc_profit = btc_gains - (btc_gains * 0.02)
    gold_profit = gold_gains - (gold_gains * 0.01)

def findNextBottomOfSpike(prediction, startDayPrice, fee):
    lowIndex = 0
    highestValue = startDayPrice
    lowestValue = startDayPrice
    for index in range(len(prediction)):
        p = prediction.iloc[index]
        if p < lowestValue:
            lowestValue = p
            lowIndex = index
        elif (p > lowestValue and highestValue - p  > (p * fee*2)):
            return lowestValue, lowIndex
        
        if (p > highestValue):
            highestValue = p

def findNextTopOfSpike(prediction, startDayPrice, fee):
    highIndex = 0
    highestValue = startDayPrice
    lowestValue = startDayPrice
    for index in range(len(prediction)):
        p = prediction.iloc[index]
        if (p > highestValue):
            highestValue = p
            highIndex = index
        elif (p < highestValue and p - lowestValue > (p * fee*2)):
            return highestValue, highIndex
        
        if p < lowestValue:
            lowestValue = p

main()