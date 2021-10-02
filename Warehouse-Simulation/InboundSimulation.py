import pandas as pd
import simpy

### INBOUND AND TIME IS IN MINUTES (VARIABLES TO CONTROL)
t_inter = 1440 #DAILY DELIVERY IS 1,440, WEEKLY DELIVERY IN MINUTES IS 10,080
sim_time = 525600  #TOTAL SIMULATION TIME, REFERENCE IS 525,600
ship_charge = 10000 #DAILY CHARGE IS $10,000 WEEKLY CHARGE IS $50,000
timeHour = 60
hrsPerDay = 24

#NUMBER OF STOWERS IS DETERMINED BY CSV SCHEDULE.

### VARIABLES NOT CONTROL - SIMULATION TIME IS IN MINUTES
RANDOM_SEED = 42
pickup = 2 #MOVING FROM INVENTORY TO INBOUND IN MINUTES, 120 SECONDS
inventory_parking = 2 #MOVING FROM INBOUND TO INVENTORY IN MINUTES, 120 SECONDS
inventory_storage = 1 #MOVING BEHIND ADJACENT STORAGE UNITS IN MINUTES, 60 SECONDS
inventory_placing = 0.16667 #PLACING EACH INDIVIDUAL UNIT IN MINUTES, 10 SECONDS
cost_per_hour = 22.50

###LOAD THE SCHEDULE
schedule = pd.read_csv("schedule.csv") #MAKE SURE YOU HAVE ASSOCIATED CSV FILE

#CREATING DICTIONARIES FOR EACH ITEM
DeliveryDict = {}
Shirts = {}
Hoodies = {}
Sweatpants = {}
Sneakers = {}
DaySchedule = {}
ShiftSchedule = {}
StowerShiftDict = {}

#LOADING CSV FILE INTO DICTIONARIES
for i in schedule.index:
    DeliveryDict[i] = schedule['DeliveryID'][i] 
    Shirts[i] = schedule['Shirts'][i] 
    Hoodies[i] = schedule['Hoodies'][i]
    DaySchedule[i] = schedule['DayWeek'][i]
    ShiftSchedule[i] = schedule['StowersPerDay'][i]
    Sweatpants[i] = schedule['Sweatpants'][i] 
    Sneakers[i] = schedule['Sneakers'][i] 

#WEIGHTS
shirts_weight = 0.5
hoodies_weight = 1
sweatpants_weight = 1
sneakers_weight = 1.5

#WEIGHTS IN DICTIONARY
Products = {"Shirts": 0.5, "Hoodies": 1, "Sweatpants": 1, "Sneakers": 1.5}

#INITIAL COUNTERS FOR COST AND TOTAL WEIGHT
Cost = 0

shirts_remaining = 0
hoodies_remaining = 0
sweatpants_remaining = 0
sneakers_remaining = 0

totalweight_shirts = 0
totalweight_hoodies = 0
totalweight_sweatpants = 0
totalweight_sneakers = 0
total_total = 0

FinalShirts = 0
FinalHoodies = 0
FinalSweatpants = 0
FinalSneakers = 0

FinalCost = {}
WeightCounter = {}

complete = 0
start = 0
StartSneakers = 0
StartHoodies = 0
Starshirtss = 0
StartSweatpants = 0

num_delivery = 0
num_trips = 0

DeliveryShirts = 0
DeliverySneakers = 0
DeliveryHoodies = 0
DeliverySweatpants = 0

completeShirts = 0
completeHoodies = 0
completeSweatpants = 0
completeSneakers = 0

totalTimeWork = 0
shirtsNum = 0
hoodiesNum = 0
sweatpantsNum = 0
sneakersNum = 0

#CREATING A STOWER CLASS
class Stower(object):

    def __init__(self, env, num_machines, pickup, inventory_parking, inventory_storage, inventory_placing):
        self.env = env
        self.machine = simpy.Resource(env, num_machines) #LIMITED RESOURCE FOR STOWER
        self.pickup = pickup
        self.inventory_parking = inventory_parking
        self.inventory_storage = inventory_storage
        self.inventory_placing = inventory_placing
    
    def picking_up_items(self, name, number):
        yield self.env.timeout(pickup)
        #print("Stower TRAVELS from INVENTORY STORAGE to INBOUND to pick up", number, name)
              
    def travel_parking_to_storage(self, name, number):
        yield self.env.timeout(inventory_parking)
        #print("Stower TRANSPORTS", number, name, "and TRAVELING from INBOUND to INVENTORY STORAGE")
        
    def stowing_unit(self, name, number):
        yield self.env.timeout(inventory_storage)
        #print("Stower circles on one trip")
        
    def placed_unit(self, name, number):
        yield self.env.timeout(round(inventory_placing * number,2))
        #print("Stower PLACED", number, name, "in INVENTORY STORAGE in", round(inventory_placing * number,2),"min")

#EACH PRODUCT WAS A RESOURCE USER
def Product(env, product, weight, stow, initialschedule):
    
    global FinalShirts, FinalHoodies, FinalSweatpants, FinalSneakers, complete, start, Starshirtss, StartHoodies, StartSweatpants, StartSneakers, completeShirts, \
    completeHoodies, completeSweatpants, completeSneakers, totalTimeWork, shirtsNum, hoodiesNum, sweatpantsNum, sneakersNum 
    
    number = weight / Products[product]
    
    start = start + 1
    
    if product == "Shirts":
        Starshirtss = Starshirtss + number
    if product == "Hoodies":
        StartHoodies = StartHoodies + number
    if product == "Sweatpants":
        StartSweatpants = StartSweatpants + number
    if product == "Sneakers":
        StartSneakers = StartSneakers + number
    
    
    with stow.machine.request() as request:
        yield request

        #print('{:.2f} {} (NEW) is READY in INBOUND parking area at TIME: {:.2f}'.format(number, product, env.now))
        yield env.process(stow.picking_up_items(product, number))
        totalTimeWork = totalTimeWork + pickup
        
        #print('{:.2f} {} is PICKED UP by STOWER in INBOUND PARKING AREA at TIME: {:.2f}'.format(number, product, env.now))
        yield env.process(stow.travel_parking_to_storage(product, number))
        totalTimeWork = totalTimeWork + inventory_parking
        
# =================================================================================
#         IF STOWERS CAN TRAVEL DIRECTLY TO THE INVENTORY STORAGE UNIT.
#           COMMENT OUT YIELDS ASSOCIATED WITH A #TRAVELORDER 
# =================================================================================
        
        #INVENTORY STORAGE 1
        if product == "Shirts":
            #print('{:.2f} {} enters the INVENTORY STORAGE at TIME: {:.2f}'.format(number, product, env.now))
            yield env.process(stow.placed_unit("Shirts", number)) #TIME STOW INDIVIDUAL UNITS
            FinalShirts = FinalShirts + number
            totalTimeWork = totalTimeWork + number * inventory_placing
            shirtsNum = shirtsNum + 1
            completeShirts = completeShirts + (pickup + inventory_parking + number * inventory_placing)
            #print('{:.2f} {} was placed in STORAGE UNIT #1 for Shirts at TIME: {:.2f}'.format(number, product, env.now))
            
        #INVENTORY STORAGE 2
        if product == "Hoodies":
            #print('{:.2f} {} enters the INVENTORY STORAGE at TIME: {:.2f}'.format(number, product, env.now))
            #yield env.process(stow.stowing_unit("Hoodies", number)) #TRAVELORDER
            yield env.process(stow.placed_unit("Hoodies", number)) #TIME STOW INDIVIDUAL UNITS
            FinalHoodies = FinalHoodies + number
            totalTimeWork = totalTimeWork + number * inventory_placing
            hoodiesNum = hoodiesNum + 1
            completeHoodies = completeHoodies + (pickup + inventory_parking + number * inventory_placing)
            #print('{:.2f} {} was placed in STORAGE UNIT #2 for Hoodies at TIME: {:.2f}'.format(number, product, env.now))
         
        #INVENTORY STORAGE 3
        if product == "Sweatpants":
            #print('{:.2f} {} enters the INVENTORY STORAGE at TIME: {:.2f}'.format(number, product, env.now))
            #yield env.process(stow.stowing_unit("Sweatpants", number)) #TRAVELORDER
            #yield env.process(stow.stowing_unit("Sweatpants", number)) #TRAVELORDER
            yield env.process(stow.placed_unit("Sweatpants", number)) #TIME STOW INDIVIDUAL UNITS
            FinalSweatpants = FinalSweatpants + number
            sweatpantsNum = sweatpantsNum + 1
            totalTimeWork = totalTimeWork + number * inventory_placing
            completeSweatpants = completeSweatpants + (pickup + inventory_parking + number * inventory_placing)
            #print('{:.2f} {} was placed in STORAGE UNIT #3 for Sweatpants at TIME: {:.2f}'.format(number, product, env.now))
            
        #INVENTORY STORAGE 4
        if product == "Sneakers":
            #print('{:.2f} {} enters the INVENTORY STORAGE at {:.2f}'.format(number, product, env.now))
            #yield env.process(stow.stowing_unit("Sneakers", number)) #TRAVELORDER
            #yield env.process(stow.stowing_unit("Sneakers", number)) #TRAVELORDER
            #yield env.process(stow.stowing_unit("Sneakers", number)) #TRAVELORDER
            yield env.process(stow.placed_unit("Sneakers", number)) #TIME STOW INDIVIDUAL UNITS
            FinalSneakers = FinalSneakers + number
            totalTimeWork = totalTimeWork + number * inventory_placing
            sneakersNum = sneakersNum + 1
            completeSneakers = completeSneakers + (pickup + inventory_parking + number * inventory_placing)
            #print('{:.2f} {} was placed in STORAGE UNIT #4 for Sneakers at TIME: {:.2f}'.format(number, product, env.now))
        
        complete = complete + 1
        
        #CLOSING RESOURCE FOR NEW SHIFT
        if env.now >= initialschedule * t_inter:
            #print("Machine in Shift:", initialschedule, "... Retired ...")
            yield env.timeout(sim_time)

        else:
            pass
            #print("Still Shift:", initialschedule, "... Machine is still working!")


def setup(env, pickup, inventory_parking, inventory_storage, inventory_placing, t_inter):
    global total_total, Cost, totalweight_shirts, totalweight_hoodies, totalweight_sweatpants, totalweight_sneakers, num_delivery, num_trips, DeliveryShirts, DeliverySneakers, DeliveryHoodies, \
            DeliverySweatpants, startingtime
    
    #CREATING A SCHEDULE COUNTER
    scheduleCounter = 0
    
    #INITIALIZATION FOR THE FIRST ROUND
    DeliveryID = DeliveryDict[scheduleCounter]
    day_week = DaySchedule[scheduleCounter]
    shirts_amount = Shirts[scheduleCounter] 
    hoodies_amount = Hoodies[scheduleCounter]
    num_stowers_shift = ShiftSchedule[scheduleCounter]
    #num_stowers_shift = 10
    sweatpants_amount = Sweatpants[scheduleCounter]
    sneakers_amount = Sneakers[scheduleCounter]

    #WEIGHT CALCULATIONS
    shirts_total = shirts_amount * shirts_weight
    hoodies_total = hoodies_amount * hoodies_weight
    sweatpants_total = sweatpants_amount * sweatpants_weight
    sneakers_total = sneakers_amount * sneakers_weight
    
    
    #OUTPUT ARRIVALS
    #print("\n=== ARRIVAL NEW SHIPMENTS ===")
    #print("Here Comes... Delivery:", DeliveryID, '.... on', day_week)
    #print(shirts_amount, "T-Shirts arrives at INBOUND PARKING at", env.now, "min")
    #print(hoodies_amount, "Hoodies arrives at INBOUND PARKING at", env.now, "min")
    #print(sweatpants_amount, "Sweat Pants arrives at INBOUND PARKING at", env.now, "min")
    #print(sneakers_amount, "Sneakers arrives at INBOUND PARKING at", env.now, "min\n")
    
    #INBOUND CALCULATIONS
    shirts_total = shirts_amount * shirts_weight
    hoodies_total = hoodies_amount * hoodies_weight
    sweatpants_total = sweatpants_amount * sweatpants_weight
    sneakers_total = sneakers_amount * sneakers_weight
    
    #INBOUND TOTAL
    inbound_total = shirts_total + hoodies_total + sweatpants_total + sneakers_total
    
    #TOTAL DELIVERY COUNT
    DeliveryShirts = DeliveryShirts + shirts_amount
    DeliverySneakers = DeliverySneakers + sneakers_amount
    DeliveryHoodies = DeliveryHoodies + hoodies_amount
    DeliverySweatpants = DeliverySweatpants + sweatpants_amount

    DeliveryHoodies = 0
    DeliverySweatpants = 0
    
    #CHECKING NUMBER OF DELIVERIES
    num_delivery = num_delivery + 1
    num_trips = num_trips + 1
    
    #COUNTER FOR ACTUAL DELIVERIES
    if inbound_total == 0:
        num_delivery = num_delivery - 1
    
    #WEIGHT COUNTERS
    WeightCounter['Shirts'] = shirts_total
    WeightCounter['Hoodies'] = hoodies_total
    WeightCounter['Sweatpants'] = sweatpants_total
    WeightCounter['Sneakers'] = sneakers_total
    
    total_total = sum(WeightCounter.values())
    #print(WeightCounter)

    #print("Current Weight Total: ", total_total)
    #print("Inbound Received: ", shirts_amount + hoodies_amount + sweatpants_amount + sneakers_amount)
    
    #CHECKING TO SEE IF OVERWEIGHT
    if total_total >= 50000:
        return_sendback = total_total - 50000
        shirts_sendback = return_sendback * (shirts_total/inbound_total)
        hoodies_sendback = return_sendback * (hoodies_total/inbound_total)
        sweatpants_sendback = return_sendback * (sweatpants_total/inbound_total)
        sneakers_sendback = return_sendback * (sneakers_total/inbound_total)
        
        WeightCounter['Shirts'] = WeightCounter['Shirts'] - shirts_sendback
        WeightCounter['Hoodies'] = WeightCounter['Hoodies'] - hoodies_sendback
        WeightCounter['Sweatpants'] = WeightCounter['Sweatpants'] - sweatpants_sendback
        WeightCounter['Sneakers'] = WeightCounter['Sneakers'] - sneakers_sendback
                    
        FinalCost[env.now] = ship_charge
        #print("Total Cost:", Cost)
        
    else:
        pass
    
    
    #CREATE THE COUNTER TO START THE TIME IN BETWEEN ARRIVAL INTERVALS
    startingtime = env.now
    currenttime = startingtime
    
    #CREATING STOWERS
    stower = Stower(env, num_stowers_shift, pickup, inventory_parking, inventory_storage, inventory_placing)
    StowerShiftDict[DeliveryID] = num_stowers_shift
    
    #WHILE THE TIME MOVE FORWARDS, STOWERS ARE BUSY TRANSPORTING THE PRODUCTS TO INVENTORY STORAGE
    while currenttime <= (startingtime + t_inter):
        if all(value == 0 for value in WeightCounter.values()) == True:
            #print("===================================")
            #print("NO INVENTORY IN INBOUND TERMINAL!!")
            #print("===================================")
            break
        else:
            sort_orders = sorted(WeightCounter.items(), key=lambda x: x[1], reverse=True)
            env.process(Product(env, sort_orders[0][0], min(12, WeightCounter[sort_orders[0][0]]), stower, DeliveryID)) #HAS TO PICK UP AT LEAST 12 POUNDS OF ONE ITEM.
            WeightCounter[sort_orders[0][0]] = WeightCounter[sort_orders[0][0]] - min(12, WeightCounter[sort_orders[0][0]])
            currenttime = currenttime + (inventory_parking + inventory_storage + inventory_placing*(min(12, WeightCounter[sort_orders[0][0]])/(Products[sort_orders[0][0]])))/(num_stowers_shift)


    #CREATE MORE SIMULATIONS AFTER THE FIRST INITIALIZATION, REPEAT OF THE INTIALIZATION (CAN CHANGE NUMBERS)
    while True:
        yield env.timeout(t_inter)
        
        #ADD TO THE SCHEDULE COUNTER
        scheduleCounter = scheduleCounter + 1
        
        #BREAKS THE SIMULATION IF WE ARE AT THE END OF OUR DEMAND SCHEDULE BUT BEFORE END SIMULATION.
        if scheduleCounter == len(DeliveryDict):
            break
    
        #INITIALIZATION
        DeliveryID = DeliveryDict[scheduleCounter]
        shirts_amount = Shirts[scheduleCounter]
        #day_week = DaySchedule[scheduleCounter]
        num_stowers_shift = ShiftSchedule[scheduleCounter]
        #num_stowers_shift = 10
        hoodies_amount = Hoodies[scheduleCounter] 
        sweatpants_amount = Sweatpants[scheduleCounter]
        sneakers_amount = Sneakers[scheduleCounter]
        
        #OUTPUT OF ARRIVALS
        #print("\n=== ARRIVAL NEW SHIPMENTS ===")
        #print("Here Comes... Delivery:", DeliveryID, '.... on', day_week)
        #print(shirts_amount, "T-Shirts arrives at INBOUND PARKING at", env.now, "min")
        #print(hoodies_amount, "Hoodies arrives at INBOUND PARKING at", env.now, "min")
        #print(sweatpants_amount, "Sweat Pants arrives at INBOUND PARKING at", env.now, "min")
        #print(sneakers_amount, "Sneakers arrives at INBOUND PARKING at", env.now, "min\n")
        
        #INBOUND CALCULATIONS
        shirts_total = shirts_amount * shirts_weight
        hoodies_total = hoodies_amount * hoodies_weight
        sweatpants_total = sweatpants_amount * sweatpants_weight
        sneakers_total = sneakers_amount * sneakers_weight
        
        #INBOUND TOTAL
        inbound_total = shirts_total + hoodies_total + sweatpants_total + sneakers_total
        
        #TOTAL DELIVERY COUNT
        DeliveryShirts = DeliveryShirts + shirts_amount
        DeliverySneakers = DeliverySneakers + sneakers_amount
        DeliveryHoodies = DeliveryHoodies + hoodies_amount
        DeliverySweatpants = DeliverySweatpants + sweatpants_amount
        
        #CHECKING NUMBER OF DELIVERIES
        num_delivery = num_delivery + 1
        num_trips = num_trips + 1
    
        if inbound_total == 0:
            num_delivery = num_delivery - 1
        
        WeightCounter['Shirts'] = WeightCounter['Shirts'] + shirts_total
        WeightCounter['Hoodies'] = WeightCounter['Hoodies'] + hoodies_total
        WeightCounter['Sweatpants'] = WeightCounter['Sweatpants'] + sweatpants_total
        WeightCounter['Sneakers'] = WeightCounter['Sneakers'] + sneakers_total
        
        total_total = sum(WeightCounter.values())

        #print(WeightCounter)
        #print("Inbound Received: ", shirts_amount + hoodies_amount + sweatpants_amount + sneakers_amount)
        
        #CHECKING TO SEE IF OVERWEIGHT
        if total_total >= 50000:
            return_sendback = total_total - 50000
            shirts_sendback = return_sendback * (shirts_total/inbound_total)
            hoodies_sendback = return_sendback * (hoodies_total/inbound_total)
            sweatpants_sendback = return_sendback * (sweatpants_total/inbound_total)
            sneakers_sendback = return_sendback * (sneakers_total/inbound_total)
            
            WeightCounter['Shirts'] = WeightCounter['Shirts'] - shirts_sendback
            WeightCounter['Hoodies'] = WeightCounter['Hoodies'] - hoodies_sendback
            WeightCounter['Sweatpants'] = WeightCounter['Sweatpants'] - sweatpants_sendback
            WeightCounter['Sneakers'] = WeightCounter['Sneakers'] - sneakers_sendback
                        
            FinalCost[env.now] = 10000
            #print("Total Cost:", Cost)
            
        else:
            pass
        
        
        startingtime = env.now
        currenttime = startingtime
        
        #STOWER
        stower = Stower(env, num_stowers_shift, pickup, inventory_parking, inventory_storage, inventory_placing)
        StowerShiftDict[DeliveryID] = num_stowers_shift
        
        #WHILE THE TIME MOVE FORWARDS, STOWERS ARE BUSY TRANSPORTING THE PRODUCTS TO INVENTORY STORAGE
        while currenttime <= (startingtime + t_inter):
            if all(value == 0 for value in WeightCounter.values()) == True:
                #print("===================================")
                #print("NO INVENTORY IN INBOUND TERMINAL!!")
                #print("===================================")
                break
            else:
                sort_orders = sorted(WeightCounter.items(), key=lambda x: x[1], reverse=True)
                env.process(Product(env, sort_orders[0][0], min(12, WeightCounter[sort_orders[0][0]]), stower, DeliveryID)) #HAS TO PICK UP AT LEAST 12 POUNDS OF ONE ITEM.
                WeightCounter[sort_orders[0][0]] = WeightCounter[sort_orders[0][0]] - min(12, WeightCounter[sort_orders[0][0]])
                currenttime = currenttime + (inventory_parking + inventory_storage + inventory_placing*(min(12, WeightCounter[sort_orders[0][0]])/(Products[sort_orders[0][0]])))/(num_stowers_shift)
        #print("Total Remaining Weight: ", sum(WeightCounter.values()))
        

#CREATE THE ENVIORNMENT AND START SIMULATION
env = simpy.Environment()
env.process(setup(env, pickup, inventory_parking, inventory_storage, inventory_placing, t_inter))

#EXECUTE
env.run(until=sim_time)

#COMPUTE THE AVERAGE STOWERS SHIFT
avgstow = sum(StowerShiftDict.values()) / len(StowerShiftDict)
employmentcost = avgstow * hrsPerDay * cost_per_hour * 365 * (sim_time/525600)

#CALCULATE TOTAL COST BASED ON STOWER WORKING
stowtravelcost = totalTimeWork/timeHour * cost_per_hour


#NUMBER OF TRIPS
print("\n=== Number of Trips (Include Trips with 0 Products) ===")
print("Number of Trips: {:,.0f}".format(num_trips))

#NUMBER OF DELIVERIES
print("\n=== Number of Actual Deliveries ===")
print("Number of Deliveries: {:,.0f}".format(num_delivery))
print("Total Delivery Cost: ${:,.2f}".format(num_delivery * ship_charge))

#STOWING TRIPS
print("\n=== Number of STOWING Trips ===")
print("Start: {:,.0f}".format(start))
print("Complete: {:,.0f}".format(complete))
print("Remaining Trips: {:,.0f}".format(start - complete))

#NUMBER OF TRIPS
print("\n=== Number of STOWING Trips per Item ===")
print("Shirts: {:,.0f}".format(shirtsNum))
print("Hoodies: {:,.0f}".format(hoodiesNum))
print("Sweatpants: {:,.0f}".format(sweatpantsNum))
print("Sneakers: {:,.0f}".format(sneakersNum))

#WORKING TIME
print("\n=== Total Min STOWING Trips (Per Work) ===")
print("Total Minutes of Work for Stowing: {:,.2f}".format(totalTimeWork))
print("Total Hours of Work for Stowing: {:,.2f}".format(totalTimeWork/timeHour))
print("Total Cost of Stowers (Work): ${:,.2f}".format(stowtravelcost))

#STOWER COST
print("\n=== Total Employment Cost (Per Hour) ===")
print("Average # of Stowers per Day: {:,.2f}".format(avgstow))
print("Total Cost of Stowers (Hours): ${:,.2f}".format(employmentcost))

#COMPLETE WORKING TIME
print("\n=== Complete Min STOWING Trips ===")
print("Complete Min for Stowing Shirts: {:,.2f}".format(completeShirts))
print("Complete Min for Stowing Hoodies: {:,.2f}".format(completeHoodies))
print("Complete Min for Stowing Sweatpants: {:,.2f}".format(completeSweatpants))
print("Complete Min for Stowing Sneakers: {:,.2f}".format(completeSneakers))
print("Total Complete Minutes of Work: {:,.2f}".format(completeShirts + completeHoodies + completeSweatpants + completeSneakers))

#SEE FORMULA BELOW

#  TOTAL DELIVERIES = INVENTORY STORAGE (FINISHED) + STOWING OPERATIONS +  
#          + REMAINING INBOUND PARKING

#TOTAL DELIVERIES
print("\n=== TOTAL Incoming Deliveries (QTY) ===")
print("Total Deliver Shirts: {:,.0f}".format(DeliveryShirts))
print("Total Deliver Hoodies: {:,.0f}".format(DeliveryHoodies))
print("Total Deliver Sweatpants: {:,.0f}".format(DeliverySweatpants))
print("Total Deliver Sneakers: {:,.0f}".format(DeliverySneakers))

#INVENTORY STORAGE 
print("\n=== Finished Inventory Storage (QTY) ===")
print("Total Shirts: {:,.0f}".format(FinalShirts))
print("Total Hoodies: {:,.0f}".format(FinalHoodies))
print("Total Sweatpants: {:,.0f}".format(FinalSweatpants))
print("Total Sneakers: {:,.0f}".format(FinalSneakers))

#STOWING OPERATIONS
print("\n=== Starting or Work in Progress Trip (QTY) ===")
print("Starting Shirts: {:,.0f}".format(Starshirtss - FinalShirts))
print("Starting Hoodies: {:,.0f}".format(StartHoodies - FinalHoodies))
print("Starting Sweatpants: {:,.0f}".format(StartSweatpants- FinalSweatpants))
print("Starting Sneakers: {:,.0f}".format(StartSneakers - FinalSneakers))

#REMAINING INBOUND PARKING
print("\n=== Remaining Inbound Parking Metrics ===")
print("Return Shipment: ${:,.2f}".format(sum(FinalCost.values())))
print("Total QTY Remaining Shirts: {:,.0f}".format(int(WeightCounter['Shirts']/shirts_weight)))
print("Total QTY Remaining Hoodies: {:,.0f}".format(int(WeightCounter['Hoodies']/hoodies_weight)))
print("Total QTY Remaining Sweatpants: {:,.0f}".format(int(WeightCounter['Sweatpants']/sweatpants_weight)))
print("Total QTY Remaining Sneakers: {:,.0f}".format(int(WeightCounter['Sneakers']/sneakers_weight)))
print("Final WEIGHT in INBOUND PARKING: {:,.2f} Pounds".format(sum(WeightCounter.values())))

#TOTAL COST CALCULATION FOR INBOUND
print("\n=== Total Inbound Charges === ")
print("FINAL INBOUND TOTAL COST: ${:,.2f}".format(employmentcost + sum(FinalCost.values()) + num_delivery * ship_charge))
