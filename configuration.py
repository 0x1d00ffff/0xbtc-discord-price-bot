


# todo: move to configuration.py
UPDATE_RATE = 120  # how often to update all APIs (in seconds)
CURRENCY = '0xBTC'
COMMAND_CHARACTER = '!'  # what character should prepend all commands



BLACKLISTED_CHANNEL_IDS = [
    # 0xbitcoin server
    '454156227446964226',  # announcements
    '417834372864147456',  # articles
    '413927301932253185',  # useful-links
    '412477591778492429',  # 0xbitcoin
    #'412483801265078273',  # trading (allowed)
    '429103257026297866',  # marketing
    '419929514316136473',  # miner-dev
    '414664710210846722',  # development
    '412483768541249536',  # support
    '438693168393748500',  # mining
    '435893447958986752',  # pools
    '439217061475123200',  # memes
    '421306695940046852',  # off-topic
    '418282243186753537',  # alts-trading

]



EXPENSIVE_STUFF = [
    (400000,
     ['lambo']),
    (200000,
     ['used lambo']),
    (500000,
     ['private island', 'privare island', 'pirvate island']),
    (398.8*1000*1000,
     ['whitehouse', 'white house']),
    (1.225*1000*1000*1000,
     ['buckingham palace']),
    (3.9*1000*1000*1000,
     ['air force one']),
    (101500, 
     ['tesla', 'telsa']),
    (1700,
     ['used ford taurus', 'used taurus', 'old ford taurus', 'old taurus']),
    (17600,
     ['like new ford taurus', 'like new taurus']),
    (28400,
     ['new ford taurus', 'ford taurus', 'new taurus', 'taurus']),
    (12,
     ['avocado toast',
      'avocado on toast', 
      'avacado toast', 
      'avacado on toast', 
      'avocato toast', 
      'avocato on toast',
      'avovado toast',
      'avo toast']),
    (1,
     ['oneaire']),
    (10,
     ['tennaire', 'tenaire']),
    (100,
     ['hundredaire', 'hundradiere']),
    (1e3,
     ['thousandaire']),
    (1e6,
     ['millionaire']),
    (1e9,
     ['billionaire']),
    (1e12,
     ['trillionaire']),
    (650,
     ['magnum domperignon', 'domperignon', 'champagne', 'donperignon']),
    (200,
     ['microsoft windows license', 'microsoft windows', 'windows']),
]
