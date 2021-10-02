"""
OUTBOUND SIMULATION PROCESS

READ ME: DEPENDENCIES
- Make sure simpy is installed
- Make sure 2 csv files (schedule.csv and order_arrival_rate.csv) and this python file are in the same folder

Components:

- Order: orders that come in random and can renenge
- Picker: Resource with deterministic time sharing one queue
- Packer: Resource with deterministic time having individual queue
- Restocking: This process happens in parallel with outbound processing

Major rules:

* We factor in picking and packing time into an order’s total waiting time to determine to process that order or not.
* We assume that there are constant inflows of inventory for each product. In the simulation, we update the inventory with that constant rate once every minute for each product.
* Inventory Holding Cost was calculated by taking the snapshots of current inventory at the end of each day and then multiplying with daily inventory holding cost for each product
* We assume the same number of pickers and packers are working throughout all days and weeks of the year

"""
import random
import datetime
import calendar
import simpy
import math
import numpy as np
import csv
import os

########################SYSTEM POLICY #################################
RANDOM_SEED = 41
START_DAY_OFFSET = 4 # Number of days to be offset from Sunday
MAX_PATIENCE = 72 * 3600  # Max. customer patience
NUM_PICKERS = 12 # Total number of pickers
NUM_PACKERS = 2 # Total number of packers
NUM_DAYS_IN_WEEK = 7
NUM_HOURS_IN_DAY = 24
NUM_WEEKS_IN_YEAR = 52
MAX_TIME = NUM_WEEKS_IN_YEAR * NUM_DAYS_IN_WEEK * NUM_HOURS_IN_DAY * 60 * 60 #in seconds
# SIM_TIME = NUM_DAYS_IN_WEEK * NUM_HOURS_IN_DAY * 60 * 60
SIM_TIME = MAX_TIME

# Beginning Inventory: value at the beginning of Simulation (00:00:00 on Thursday)
ProductBeginningInventory = { 
    'Shirts':10000, 'Hoodies':5000, 
    'Sweatpants':5000, 'Sneakers':3333
}

################## DICTIONARY FOR MAPPING ##################
ProductDemandLambda = { # np.exponential takes the inverse of lambda as parameters
    'Shirts':1/0.94, 'Hoodies':1/1.73,
    'Sweatpants':1/1.72, 'Sneakers':1/2.85
}

ProductInventoryAreaMapping = {
 'Hoodies':2, 'Shirts':1,
 'Sneakers':4, 'Sweatpants':3
}

# number of weeks for simulation times
scale =  SIM_TIME / (NUM_DAYS_IN_WEEK*NUM_HOURS_IN_DAY*3600) 


ProductHoldingCost = {
    'Shirts':0.1, 'Hoodies':0.3, 
    'Sweatpants':0.3, 'Sneakers':0.6 
}

ProductGrossProfit = {
    'Shirts':4, 'Hoodies':10, 
    'Sweatpants':10, 'Sneakers':20 
}

ProductLossProfit = {
    'Shirts':1, 'Hoodies':6, 
    'Sweatpants':6, 'Sneakers':10 
}

################LIST TO TRACk KPI###################

grossProfit = []
lostSalesStockOut = []
lostSalesLate = []
laborExpense = []
facilitiesFixedCost = []
packingStationExpense = []
inventoryHoldingCost = []
orderWaitTime = []
dailyEndingInventory = []
ProductCurrentInventory = ProductBeginningInventory

################LIST TO TRACK Performance###################

totalOrdersPicked = []
totalOrdersPacked = []
totalPickerWaitTime = []
totalPackerWaitTime = []
################LIST TO TRACk Demand###################

totalOrders = []

######################################################

def source(env, picker, packer):
    """Source generates orders randomly"""
    i=0
    #Read the order arrival model parameters
    weeklyOrderArrivalRates = readWeeklyOrderArrivalRates()
    while True:
        details = generateOrderDetails()
        o = order(env, 'Order %02d' % i, picker, packer, details)
        env.process(o)
        # Arrival Rate varies based on hour of day and day of the week
        ar = getOrderArrivalRates(env.now,weeklyOrderArrivalRates)
        t = np.random.exponential(1/ar)
        yield env.timeout(t)
        i+=1

def readWeeklyOrderArrivalRates():
    '''Read the Order Arrival Rate '''
    out = {}
    dirname = os.path.dirname(__file__)
    reader = csv.DictReader(open(os.path.join(dirname,"order_arrival_rate.csv"),"r"))

    for row in reader:
        out[(row['DayofWeek'],int(row['HourofDay']))] = float(row['Parameter'])   
    return out

def getOrderArrivalRates(t,mapping):
    '''Return Order Arrival Rate based on time '''
    #convert time to day in week
    delta = datetime.timedelta(seconds=t)
    days = delta.days + START_DAY_OFFSET
    h = math.floor(delta.seconds / 3600 )
    #convert time to hour in day
    #take into account when offset days go to next week
    remainder = ((days-1) % 7)
    d = calendar.day_name[remainder]
    # print('Day: %s , Hour: %d' %(d,h))
    return mapping[(d,h)]

def generateOrderDetails():
    """generates quanties in each order randomly"""
    shirts, hoodies, sweatpants, sneakers = 0,0,0,0
    while all(i == 0 for i in [shirts,hoodies,sweatpants,sneakers]):
    # If all products in an order is 0, repeat the generation
        shirts = round(np.random.exponential(ProductDemandLambda['Shirts']))
        hoodies =  round(np.random.exponential(ProductDemandLambda['Hoodies']))
        sweatpants = round(np.random.exponential(ProductDemandLambda['Sweatpants']))
        sneakers = round(np.random.exponential(ProductDemandLambda['Sneakers']))
    
    out = {'Shirts':shirts,'Hoodies': hoodies, 'Sweatpants':sweatpants,'Sneakers':sneakers }
    return out

def order(env, name, picker, packer, orderDetails):
    """Order arrives, is served and packed."""
    arrive = env.now
    # print('%7.4f %s: Order arrives: %s' % (arrive, name, ','.join([str(i) for i in orderDetails.items()])))
    totalOrders.append(orderDetails)

    with picker.request() as req:
        # Wait for the counter or abort at the end of 72 hours
        patience = MAX_PATIENCE
        results = yield req | env.timeout(patience)
        wait = env.now - arrive
        totalPickerWaitTime.append(wait)
        # Calculate picking time based on order details
        time_in_picking = getPickingTime(orderDetails)
        # If wait plus time in picking exceed 72 hours, cancel order (Order will be cancelled in the middle of picking)
        if wait + time_in_picking >= MAX_PATIENCE:
            # print('%7.4f %s: Waited for picker %6.3f' % (env.now, name, wait+time_in_picking)) 
            cancelOrder(orderDetails, "Wait Time + Picking Time exceed limits")
        # If current inventory cannot fulfill the current order, cancel order
        # Patial fulfillment is not allowed, cancel if any part of the order is short
        elif checkOrderAgainstCurrentInventory(orderDetails):
            # print('Current Inventory: %s' % (','.join([str(i) for i in ProductCurrentInventory.items()])))
            cancelOrder(orderDetails, "Run out of inventory for product")
        elif req in results:
            # We got to the picker
            # print('%7.4f %s: Waited for picker %6.3f' % (env.now, name, wait))               
            # print('Time in Picking: %7.4f' % (time_in_picking))
            yield env.timeout(time_in_picking)
            totalOrdersPicked.append(1)
            # print('%7.4f %s: Picking Finished' % (env.now, name))
            # Picker pick next order and Packer is trigger
            p = packOrder(env,name,packer,orderDetails,arrive)
            env.process(p)
        else:
            # Order cancelled
            # print('%7.4f %s: CANCELLED after %6.3f' % (env.now, name, wait))
            cancelOrder(orderDetails, "Wait Time exceed limits")
            #[rev1 2020-09-11: If the order is cancelled before the start of the picking
            # operation, the inventory will NOT be lost. However, lost sales penalty still applies.]

def packOrder(env,name,packer,orderDetails,firstArrive):
    """Packing operations"""
    arrive = env.now
    Qlength = [NoInSystem(packer[i]) for i in range(NUM_PACKERS)]
    # print("%7.4f %s: Here I am in front of packing station. %s" %(arrive,name,Qlength))
    # Choose the packers with shortest queue length
    for i in range(NUM_PACKERS):                                         
        if Qlength[i] == 0 or Qlength[i] == min(Qlength):
            choice = i  # the chosen queue number                
            break
    # Process happens at the packer:
    with packer[choice].request() as req:
        # Wait for the packer or abort at the end of 72 hours
        patience = MAX_PATIENCE-(arrive-firstArrive)
        results = yield req | env.timeout(patience)
        wait = env.now - arrive
        totalPackerWaitTime.append(wait)
        # Calculate picking time based on order details
        time_in_packing = getPackingTime(orderDetails)
        # If wait plus time in packing exceed 72 hours, cancel order
        if wait + time_in_packing >= patience:
            # print('%7.4f %s: Waited for packer %6.3f' % (env.now, name, wait+time_in_packing)) 
            cancelOrder(orderDetails, "Wait Time + Packing Time exceed limits")
        elif req in results:
            # We got to the packer
            # print('%7.4f %s: Waited for packer %6.3f' % (env.now, name, wait))               
            # print('Time in Packing: %7.4f' % (time_in_packing))
            yield env.timeout(time_in_packing)
            totalOrdersPacked.append(1)
            # print('%7.4f %s: Packing Finished' % (env.now, name))
            # Book Gross Profits
            grossP = sum([ProductGrossProfit[p]*q for p,q in orderDetails.items()])
            # print('Revenue Booked: %d' %(grossP))
            grossProfit.append(grossP)
            # Subtract Inventory
            subtractInventory(orderDetails)
            # print('Current Inventory: %s' % (','.join([str(i) for i in ProductCurrentInventory.items()])))
        else:
            # Order cancelled
            # print('%7.4f %s: CANCELLED after %6.3f' % (env.now, name, wait))
            cancelOrder(orderDetails,"Wait Time exceed limits")
            # Subtract Inventory
            subtractInventory(orderDetails)
            # print('Current Inventory: %s' % (','.join([str(i) for i in ProductCurrentInventory.items()])))

def restockInventory(env):
    '''Model the inflow of inventory'''
    global ProductCurrentInventory
    restockRate = {}
    today_value = 0
    ds = readDeliverySchedule()
    while True: # Update inventory every 60 seconds
        # Get total number of days since simulation starts
        today = env.now // (3600 * 24) + 1
        # Determine restocking rate (per min) for the day
        if today != today_value: 
            # Only do this once a day
            today_value = today
            for k,v in ds[str(today)].items():   
                restockRate[k] = int(v) / (60*24)
            # Print every n days
            if today % 60 == 0:
                print('Day %d' %today)
                # Current Inventory
                print('Current Inventory -- Shirts: %d, Hoodies: %d, Sweatpants: %d, Sneakers: %d' % \
                tuple(ProductCurrentInventory.values()))
                    # print(restockRate)
            
            # Rounding Product Current Inventory (Due to fraction in restock rate)
            roundInventory()
            # Track the Ending Inventory of the last day
            dailyEndingInventory.append(ProductCurrentInventory)
        else:
            # Restock
            for k,v in restockRate.items():
                ProductCurrentInventory[k] = ProductCurrentInventory[k] + v
        # Wait 60 seconds
        yield env.timeout(60)

def readDeliverySchedule():
    out = {}
    dirname = os.path.dirname(__file__)
    reader = csv.DictReader(open(os.path.join(dirname,"schedule.csv"),"r"))

    for row in reader:
        out[row['DeliveryID']] = {'Shirts':row['Shirts'], 'Hoodies':row['Hoodies'], 
    'Sweatpants':row['Sweatpants'], 'Sneakers':row['Sneakers'] }
    return out


def cancelOrder(orderDetails,cancelReason):
    # Book lost sales
    lossP = sum([ProductLossProfit[p]*q for p,q in orderDetails.items()])
    # print('Cancel Orders: %s. Lost Sales Booked %d' %(cancelReason, lossP))
    if cancelReason == 'Run out of inventory for product':
        lostSalesStockOut.append(lossP)
    else:
        lostSalesLate.append(lossP)

def NoInSystem(R):                                                  
    """ Total number of orders in the resource R"""
    return (len(R.queue)+len(R.users))   


def checkOrderAgainstCurrentInventory(orderDetails):
    for p, q in ProductCurrentInventory.items():
        if orderDetails[p] > q:
            return True
    return False

def getPickingTime(orderDetails):
    time_in_picking = 0
    currentPosition = ''
    for p,q in orderDetails.items():
        nextPosition = ProductInventoryAreaMapping[p]
        if q == 0:
            continue
        elif currentPosition == '':
            #Move to inventory area
            currentPosition = nextPosition
            time_in_picking = time_in_picking + 120
            #Picking
            time_in_picking = time_in_picking + (q * (10))
        else:
            # Calculate number of steps between current and next inventory area
            steps = nextPosition - currentPosition
            #Move to adjacent area
            currentPosition = nextPosition
            time_in_picking = time_in_picking + (60 * steps)
            #Picking
            time_in_picking = time_in_picking + (q * (10))
    # Once done, move back to picking station & send order to packing station
    time_in_picking = time_in_picking + 120 + 30 
    return time_in_picking

def getPackingTime(orderDetails):
    out = 0
    for p,q in orderDetails.items():
        out = out + (q * 10)
    return (out + 30)

def subtractInventory(orderDetails):
    global ProductCurrentInventory
    for p,q in orderDetails.items():
        ProductCurrentInventory[p] = ProductCurrentInventory[p] - q

def roundInventory():
    global ProductCurrentInventory
    for k,v in ProductCurrentInventory.items():
                ProductCurrentInventory[k] = round(v)

def getInventoryHoldingCost():
    out = {
    'Shirts':0, 'Hoodies':0, 
    'Sweatpants':0, 'Sneakers':0 
    }
    roundInventory()
    # Current Inventory
    print('Ending Inventory -- Shirts: %d, Hoodies: %d, Sweatpants: %d, Sneakers: %d' % \
            tuple(ProductCurrentInventory.values()))
    # Aggreate Holding Cost w Daily Ending Inventory

    for d in dailyEndingInventory:   
        for p,q in d.items():
            out[p] = out[p] + q * ProductHoldingCost[p]

    return list(out.values())

def getLaborCost():
    pickerCost = 22.5 * NUM_PICKERS / 3600 * SIM_TIME
    packerCost = 22.5 * NUM_PACKERS / 3600 * SIM_TIME
    return [pickerCost,packerCost]

def getFacilitiesFixedCost():
    fixedCost = 5000000 / MAX_TIME * SIM_TIME
    packingStationCost = 50000 * NUM_PACKERS / MAX_TIME * SIM_TIME
    return [fixedCost,packingStationCost]

def getTotalOrderDetails():
    out = {
    'Shirts':0, 'Hoodies':0, 
    'Sweatpants':0, 'Sneakers':0 
    }
    for i in totalOrders:
        for p,q in i.items():
            out[p] = out[p] + q

    return out


# Setup and start the simulation
def runSimulation(numPickers,numPackers):
    global NUM_PICKERS,NUM_PACKERS
    ################LIST TO TRACk KPI###################
    global dailyEndingInventory,grossProfit,lostSalesStockOut,lostSalesLate, \
    laborExpense,facilitiesFixedCost,packingStationExpense,inventoryHoldingCost, \
        orderWaitTime, ProductCurrentInventory
    #Reset the global vars before simulation starts
    grossProfit = []
    lostSalesStockOut = []
    lostSalesLate = []
    laborExpense = []
    facilitiesFixedCost = []
    packingStationExpense = []
    inventoryHoldingCost = []
    orderWaitTime = []
    dailyEndingInventory = []
    ProductCurrentInventory = { 
    'Shirts':10000, 'Hoodies':5000, 
    'Sweatpants':5000, 'Sneakers':3333
    }
    # # Current Inventory
    # print('Current Inventory -- Shirts: %d, Hoodies: %d, Sweatpants: %d, Sneakers: %d' % \
    #         tuple(ProductCurrentInventory.values()))


    ################LIST TO TRACK Performance###################
    global totalOrdersPicked,totalOrdersPacked,totalPickerWaitTime,totalPackerWaitTime
    totalOrdersPicked = []
    totalOrdersPacked = []
    totalPickerWaitTime = []
    totalPackerWaitTime = []
    ################LIST TO TRACk Demand###################
    global totalOrders
    totalOrders = []

    ######################################################

    NUM_PICKERS,NUM_PACKERS = numPickers,numPackers
    print('----------------Outbound Processing Simulation-------------')
    print('-NUM PICKERS: %d ------NUM PACKERS: %d -------' %(NUM_PICKERS,NUM_PACKERS))
    random.seed(RANDOM_SEED)
    env = simpy.Environment()

    # Start processes and run
    picker = simpy.Resource(env, capacity=NUM_PICKERS)
    packer = [simpy.Resource(env, capacity=1) for i in range(NUM_PACKERS)]
    env.process(source(env, picker, packer))
    env.process(restockInventory(env))
    env.run(until=SIM_TIME)

    # Calculate Fixed & Variable Cost
    inventoryHoldingCost = getInventoryHoldingCost()
    laborExpense = getLaborCost()
    facilitiesFixedCost = getFacilitiesFixedCost()

    # Analysis
    ''' Tracking throughput & queue performance
        - Picker Throughput
        - Packer Throughput
        - Average wait picker time
        - Average wait packer time
    '''
    print('Picker Throughput: %.2f orders per minute' % ((len(totalOrdersPicked)/SIM_TIME)*60))
    print('Packer Throughput: %.2f orders per minute' % ((len(totalOrdersPacked)/SIM_TIME)*60))
    print('Average order wait time for picker: %.2f hours' % (np.sum(totalPickerWaitTime)/len(totalOrdersPicked)/3600))
    print('Average order wait time for packer: %.2f hours' % (np.sum(totalPackerWaitTime)/len(totalOrdersPacked)/3600))


    ''' Tracking weekly demand (Validate order arrival model)'''
    
    print('Total Orders Arrived: %d' %(len(totalOrders)))
    print('Weekly Orders Arrived: %d' %(len(totalOrders) // scale)) 
    tod = getTotalOrderDetails()
    wk_tod = {key: value // scale for (key,value) in tod.items()}
    print('Total -- Shirts: %d, Hoodies: %d, Sweatpants: %d, Sneakers: %d' % \
                tuple(tod.values()))
    print('Weekly Avg -- Shirts: %d, Hoodies: %d, Sweatpants: %d, Sneakers: %d' % \
                tuple(wk_tod.values()))

    # KPI
    print('/n Total Revenue: $%d' %(np.sum(grossProfit)))
    print('Less Lost Sales Penalty (StockOut): -$%d' %(np.sum(lostSalesStockOut)))
    print('Less Lost Sales Penalty (Late Processing): -$%d' %(np.sum(lostSalesLate)))
    print('Less Labor Cost: -$%d' %(np.sum(laborExpense)))
    print('Less Facility Cost + Packing Station Expense: -$%d' %(np.sum(facilitiesFixedCost)))
    print('Less Inventory Holding Cost: -$%d' %(round(np.sum(inventoryHoldingCost))))
    print('Net Profit: $%d '% (np.sum(grossProfit) - np.sum(lostSalesStockOut) - np.sum(lostSalesLate) - np.sum(inventoryHoldingCost) \
                    - np.sum(laborExpense) - np.sum(facilitiesFixedCost) ))


# TESTING DIFFERENT POLICIES

policies = [[12,2]]

for policy in policies:
    runSimulation(policy[0],policy[1])