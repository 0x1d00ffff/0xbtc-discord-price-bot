"""
API for Bithumb DEX (bithumb.io)

https://api.bithumb.io/api/v2/ticker/list?baseToken=ETH

response:

{"code":0,
"message":"Success",
"data":{
    "total":12,
    "result":[{
        "id":80,
        "tokenName":"WTC",
        "baseName":"ETH",
        "lastDayPrice":"0.016831000000000000",
        "price":"0.016831000000000000",
        "lastPrice":"0.016830000000000000",
        "rise":"0.00000000",
        "tradeTokenAmount":"0.00000000",
        "tradeBaseAmount":"0.00000000",
        "highPrice24h":"0.00000000",
        "lowPrice24h":"0.00000000",
        "highestBid":"0.00000000",
        "lowestAsk":"0.00000000",
        "priceScale":6,
        "amountScale":2,
        "depthRule":"-6,-5,-4",
        "status":1,
        "sort":0,
        "created_at":"2018-09-15 16:29:41",
        "updated_at":"2018-11-13 07:00:11",
        "flag":0,
        "fullName":"Walton",
        "symbol":"WTC_ETH"
    },{
        "id":10,
        "tokenName":"OMG",
        "baseName":"ETH",
        "lastDayPrice":"0.015570000000000000",
        "price":"0.015830000000000000",
        "lastPrice":"0.015830000000000000",
        "rise":"1.66987797",
        "tradeTokenAmount":"2482532.15000000",
        "tradeBaseAmount":"38701.24975640",
        "highPrice24h":"0.01583000",
        "lowPrice24h":"0.01522000",
        "highestBid":"0.00000000",
        "lowestAsk":"0.00000000",
        "priceScale":6,
        "amountScale":2,
        "depthRule":"-6,-5,-4",
        "status":1,
        "sort":0,
        "created_at":"2018-05-09 17:26:11",
        "updated_at":"2018-11-13 07:00:11",
        "flag":0,
        "fullName":"OmiseGo",
        "symbol":"OMG_ETH"
    },

    ...

    ]}}


"""