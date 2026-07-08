/* SAMPLE DATA — illustrative figures for interface development only.
   Schema modeled on the State Controller's Office city annual financial
   reports (bythenumbers.sco.ca.gov). Run pipeline/fetch_city_data.py to
   replace with official data. Do not cite these numbers. */
window.CA_CITY_DATA = {
  "meta": {
    "source": "SAMPLE",
    "sourceLabel": "Sample data modeled on State Controller's Office city annual financial reports (bythenumbers.sco.ca.gov)",
    "generated": "2026-07-08",
    "units": "millions of dollars"
  },
  "years": [
    "2021-22",
    "2022-23",
    "2023-24"
  ],
  "functions": [
    {
      "key": "police",
      "name": "Police"
    },
    {
      "key": "fire",
      "name": "Fire"
    },
    {
      "key": "streets",
      "name": "Streets & transportation"
    },
    {
      "key": "parks",
      "name": "Parks & recreation"
    },
    {
      "key": "library",
      "name": "Libraries & culture"
    },
    {
      "key": "housing",
      "name": "Community development & housing"
    },
    {
      "key": "sanitation",
      "name": "Sewer & sanitation"
    },
    {
      "key": "health",
      "name": "Health & welfare"
    },
    {
      "key": "admin",
      "name": "General administration"
    },
    {
      "key": "debt",
      "name": "Debt service"
    }
  ],
  "cities": {
    "los-angeles": {
      "name": "Los Angeles",
      "county": "Los Angeles",
      "years": {
        "2021-22": {
          "population": 3825300,
          "revenues": 10370.9,
          "expenditures": 10291.7,
          "byFunction": {
            "police": 2642.6,
            "fire": 1017.3,
            "streets": 961,
            "parks": 620.7,
            "library": 303.6,
            "housing": 891,
            "sanitation": 1429.7,
            "health": 443.9,
            "admin": 1275.2,
            "debt": 706.7
          }
        },
        "2022-23": {
          "population": 3822700,
          "revenues": 11508.5,
          "expenditures": 10700.4,
          "byFunction": {
            "police": 2749.9,
            "fire": 1054.8,
            "streets": 1006,
            "parks": 636.4,
            "library": 328.8,
            "housing": 909.4,
            "sanitation": 1529.8,
            "health": 444.5,
            "admin": 1284.7,
            "debt": 756.1
          }
        },
        "2023-24": {
          "population": 3820000,
          "revenues": 11334.4,
          "expenditures": 11104.3,
          "byFunction": {
            "police": 2861.5,
            "fire": 1121.8,
            "streets": 1065.2,
            "parks": 634.6,
            "library": 327.7,
            "housing": 945.6,
            "sanitation": 1513.5,
            "health": 473.6,
            "admin": 1371.9,
            "debt": 788.9
          }
        }
      }
    },
    "san-diego": {
      "name": "San Diego",
      "county": "San Diego",
      "years": {
        "2021-22": {
          "population": 1381700,
          "revenues": 3126.1,
          "expenditures": 2970.1,
          "byFunction": {
            "police": 664,
            "fire": 305.6,
            "streets": 325.8,
            "parks": 218,
            "library": 98.3,
            "housing": 321.5,
            "sanitation": 287.8,
            "health": 182.1,
            "admin": 348.9,
            "debt": 218.1
          }
        },
        "2022-23": {
          "population": 1384800,
          "revenues": 3321.4,
          "expenditures": 3086,
          "byFunction": {
            "police": 682.1,
            "fire": 318.6,
            "streets": 349.6,
            "parks": 221.7,
            "library": 105.3,
            "housing": 341.4,
            "sanitation": 309.7,
            "health": 184.8,
            "admin": 349.8,
            "debt": 223
          }
        },
        "2023-24": {
          "population": 1388000,
          "revenues": 3291.3,
          "expenditures": 3199.5,
          "byFunction": {
            "police": 710.6,
            "fire": 322.1,
            "streets": 357.4,
            "parks": 231.9,
            "library": 110.3,
            "housing": 347.2,
            "sanitation": 321.8,
            "health": 191.1,
            "admin": 377.8,
            "debt": 229.3
          }
        }
      }
    },
    "san-jose": {
      "name": "San Jose",
      "county": "Santa Clara",
      "years": {
        "2021-22": {
          "population": 971500,
          "revenues": 1959.8,
          "expenditures": 1924.8,
          "byFunction": {
            "police": 419.1,
            "fire": 286.5,
            "streets": 196.9,
            "parks": 143,
            "library": 55.5,
            "housing": 191,
            "sanitation": 160.5,
            "health": 88.8,
            "admin": 224.9,
            "debt": 158.6
          }
        },
        "2022-23": {
          "population": 970300,
          "revenues": 2098,
          "expenditures": 2050.7,
          "byFunction": {
            "police": 446.9,
            "fire": 305,
            "streets": 212.6,
            "parks": 142.1,
            "library": 60.6,
            "housing": 204.8,
            "sanitation": 167.1,
            "health": 96,
            "admin": 243.1,
            "debt": 172.5
          }
        },
        "2023-24": {
          "population": 969000,
          "revenues": 2165.6,
          "expenditures": 2109.2,
          "byFunction": {
            "police": 456.3,
            "fire": 306.9,
            "streets": 217,
            "parks": 151,
            "library": 64.1,
            "housing": 212.3,
            "sanitation": 176.3,
            "health": 95.8,
            "admin": 248.6,
            "debt": 180.9
          }
        }
      }
    },
    "fresno": {
      "name": "Fresno",
      "county": "Fresno",
      "years": {
        "2021-22": {
          "population": 545900,
          "revenues": 721.1,
          "expenditures": 754.8,
          "byFunction": {
            "police": 172,
            "fire": 74.7,
            "streets": 101.3,
            "parks": 50.5,
            "library": 22.2,
            "housing": 63.7,
            "sanitation": 100.4,
            "health": 25,
            "admin": 92.2,
            "debt": 52.8
          }
        },
        "2022-23": {
          "population": 545400,
          "revenues": 770.3,
          "expenditures": 788.6,
          "byFunction": {
            "police": 178.3,
            "fire": 80.3,
            "streets": 107,
            "parks": 53.8,
            "library": 23.8,
            "housing": 65.7,
            "sanitation": 105.2,
            "health": 25.7,
            "admin": 93,
            "debt": 55.8
          }
        },
        "2023-24": {
          "population": 545000,
          "revenues": 840.5,
          "expenditures": 815.2,
          "byFunction": {
            "police": 187.5,
            "fire": 81.7,
            "streets": 109.4,
            "parks": 56.2,
            "library": 24.6,
            "housing": 68.6,
            "sanitation": 104.8,
            "health": 26.6,
            "admin": 98.5,
            "debt": 57.3
          }
        }
      }
    },
    "sacramento": {
      "name": "Sacramento",
      "county": "Sacramento",
      "years": {
        "2021-22": {
          "population": 527900,
          "revenues": 979.6,
          "expenditures": 929.8,
          "byFunction": {
            "police": 239.9,
            "fire": 107.7,
            "streets": 123,
            "parks": 60.6,
            "library": 22.8,
            "housing": 58.6,
            "sanitation": 111.9,
            "health": 36,
            "admin": 102.3,
            "debt": 67
          }
        },
        "2022-23": {
          "population": 526900,
          "revenues": 957.2,
          "expenditures": 958.1,
          "byFunction": {
            "police": 249.8,
            "fire": 108.7,
            "streets": 129,
            "parks": 63.6,
            "library": 22.4,
            "housing": 61.4,
            "sanitation": 114.8,
            "health": 38.7,
            "admin": 102.2,
            "debt": 67.5
          }
        },
        "2023-24": {
          "population": 526000,
          "revenues": 1014.8,
          "expenditures": 995.4,
          "byFunction": {
            "police": 253.4,
            "fire": 116.3,
            "streets": 133.8,
            "parks": 64.9,
            "library": 23.4,
            "housing": 62.8,
            "sanitation": 123.4,
            "health": 38.9,
            "admin": 105.5,
            "debt": 73
          }
        }
      }
    },
    "long-beach": {
      "name": "Long Beach",
      "county": "Los Angeles",
      "years": {
        "2021-22": {
          "population": 449500,
          "revenues": 1023.9,
          "expenditures": 969.4,
          "byFunction": {
            "police": 226.8,
            "fire": 86.6,
            "streets": 125.7,
            "parks": 88.2,
            "library": 25.9,
            "housing": 82.8,
            "sanitation": 139.5,
            "health": 41.9,
            "admin": 104.3,
            "debt": 47.7
          }
        },
        "2022-23": {
          "population": 450200,
          "revenues": 987.4,
          "expenditures": 1019.4,
          "byFunction": {
            "police": 241.7,
            "fire": 93.1,
            "streets": 129.9,
            "parks": 94.4,
            "library": 28.3,
            "housing": 89.1,
            "sanitation": 142.7,
            "health": 43,
            "admin": 105.9,
            "debt": 51.3
          }
        },
        "2023-24": {
          "population": 451000,
          "revenues": 1116.7,
          "expenditures": 1070.1,
          "byFunction": {
            "police": 251.3,
            "fire": 95.2,
            "streets": 139.1,
            "parks": 99.8,
            "library": 30.3,
            "housing": 93.1,
            "sanitation": 148.4,
            "health": 45.3,
            "admin": 114.7,
            "debt": 52.9
          }
        }
      }
    },
    "oakland": {
      "name": "Oakland",
      "county": "Alameda",
      "years": {
        "2021-22": {
          "population": 433400,
          "revenues": 1072,
          "expenditures": 1056.6,
          "byFunction": {
            "police": 293.9,
            "fire": 99.8,
            "streets": 97.1,
            "parks": 65,
            "library": 36.2,
            "housing": 110,
            "sanitation": 99.5,
            "health": 49.2,
            "admin": 130.2,
            "debt": 75.7
          }
        },
        "2022-23": {
          "population": 434700,
          "revenues": 1062.3,
          "expenditures": 1083.4,
          "byFunction": {
            "police": 300.2,
            "fire": 102.9,
            "streets": 102.9,
            "parks": 67.3,
            "library": 38,
            "housing": 111.2,
            "sanitation": 99.8,
            "health": 50.1,
            "admin": 135.3,
            "debt": 75.7
          }
        },
        "2023-24": {
          "population": 436000,
          "revenues": 1103.3,
          "expenditures": 1124.8,
          "byFunction": {
            "police": 305.6,
            "fire": 102.8,
            "streets": 109.7,
            "parks": 70.6,
            "library": 38.7,
            "housing": 117.5,
            "sanitation": 106.8,
            "health": 53.4,
            "admin": 137.5,
            "debt": 82.2
          }
        }
      }
    },
    "bakersfield": {
      "name": "Bakersfield",
      "county": "Kern",
      "years": {
        "2021-22": {
          "population": 409800,
          "revenues": 466.5,
          "expenditures": 487.7,
          "byFunction": {
            "police": 105.5,
            "fire": 56.3,
            "streets": 51.2,
            "parks": 37.9,
            "library": 22.7,
            "housing": 39.7,
            "sanitation": 51.9,
            "health": 31.2,
            "admin": 54.6,
            "debt": 36.7
          }
        },
        "2022-23": {
          "population": 411400,
          "revenues": 486.5,
          "expenditures": 511,
          "byFunction": {
            "police": 110.2,
            "fire": 60.9,
            "streets": 52.7,
            "parks": 40.4,
            "library": 23.5,
            "housing": 42.4,
            "sanitation": 54.6,
            "health": 31.6,
            "admin": 57.9,
            "debt": 36.8
          }
        },
        "2023-24": {
          "population": 413000,
          "revenues": 575.9,
          "expenditures": 537.2,
          "byFunction": {
            "police": 113.5,
            "fire": 64.5,
            "streets": 57.6,
            "parks": 41.7,
            "library": 25.3,
            "housing": 42.9,
            "sanitation": 56.2,
            "health": 34.8,
            "admin": 61.3,
            "debt": 39.4
          }
        }
      }
    },
    "anaheim": {
      "name": "Anaheim",
      "county": "Orange",
      "years": {
        "2021-22": {
          "population": 340700,
          "revenues": 720.2,
          "expenditures": 667.8,
          "byFunction": {
            "police": 157.9,
            "fire": 96.7,
            "streets": 54.4,
            "parks": 42.8,
            "library": 18.3,
            "housing": 72.8,
            "sanitation": 94.2,
            "health": 24.8,
            "admin": 56.4,
            "debt": 49.5
          }
        },
        "2022-23": {
          "population": 340400,
          "revenues": 670.5,
          "expenditures": 694.1,
          "byFunction": {
            "police": 169.1,
            "fire": 99.1,
            "streets": 58.3,
            "parks": 43.8,
            "library": 19,
            "housing": 75.2,
            "sanitation": 97.1,
            "health": 25.3,
            "admin": 57.4,
            "debt": 49.8
          }
        },
        "2023-24": {
          "population": 340000,
          "revenues": 698.4,
          "expenditures": 711.4,
          "byFunction": {
            "police": 165.8,
            "fire": 105.9,
            "streets": 60.7,
            "parks": 44.8,
            "library": 19.1,
            "housing": 77.3,
            "sanitation": 100.6,
            "health": 26.5,
            "admin": 57.9,
            "debt": 52.8
          }
        }
      }
    },
    "stockton": {
      "name": "Stockton",
      "county": "San Joaquin",
      "years": {
        "2021-22": {
          "population": 322000,
          "revenues": 444.1,
          "expenditures": 417.1,
          "byFunction": {
            "police": 73,
            "fire": 62.3,
            "streets": 45.7,
            "parks": 37.2,
            "library": 15,
            "housing": 47.2,
            "sanitation": 43,
            "health": 15.7,
            "admin": 49.9,
            "debt": 28.1
          }
        },
        "2022-23": {
          "population": 321500,
          "revenues": 423.6,
          "expenditures": 435,
          "byFunction": {
            "police": 76.6,
            "fire": 63.5,
            "streets": 49.1,
            "parks": 37.6,
            "library": 15.4,
            "housing": 48.7,
            "sanitation": 46.4,
            "health": 17.1,
            "admin": 52.3,
            "debt": 28.3
          }
        },
        "2023-24": {
          "population": 321000,
          "revenues": 443.7,
          "expenditures": 450,
          "byFunction": {
            "police": 78,
            "fire": 67.2,
            "streets": 51.8,
            "parks": 38.7,
            "library": 15.6,
            "housing": 51.8,
            "sanitation": 47.3,
            "health": 17.6,
            "admin": 52.9,
            "debt": 29.1
          }
        }
      }
    },
    "riverside": {
      "name": "Riverside",
      "county": "Riverside",
      "years": {
        "2021-22": {
          "population": 315600,
          "revenues": 516.7,
          "expenditures": 531.8,
          "byFunction": {
            "police": 140.6,
            "fire": 45.3,
            "streets": 62.9,
            "parks": 44.3,
            "library": 20.8,
            "housing": 43.7,
            "sanitation": 47.6,
            "health": 23.5,
            "admin": 65.9,
            "debt": 37.2
          }
        },
        "2022-23": {
          "population": 316800,
          "revenues": 534.1,
          "expenditures": 550.5,
          "byFunction": {
            "police": 139.3,
            "fire": 47.8,
            "streets": 64.2,
            "parks": 47.6,
            "library": 21.2,
            "housing": 44.8,
            "sanitation": 50.7,
            "health": 25.6,
            "admin": 70.7,
            "debt": 38.6
          }
        },
        "2023-24": {
          "population": 318000,
          "revenues": 554.8,
          "expenditures": 568.6,
          "byFunction": {
            "police": 145.2,
            "fire": 48.2,
            "streets": 67.7,
            "parks": 47.9,
            "library": 21.4,
            "housing": 46.9,
            "sanitation": 51.5,
            "health": 26.8,
            "admin": 72.5,
            "debt": 40.5
          }
        }
      }
    },
    "irvine": {
      "name": "Irvine",
      "county": "Orange",
      "years": {
        "2021-22": {
          "population": 315100,
          "revenues": 444.4,
          "expenditures": 463.4,
          "byFunction": {
            "police": 90.3,
            "fire": 55.7,
            "streets": 40.4,
            "parks": 42.6,
            "library": 17.4,
            "housing": 49.8,
            "sanitation": 53.1,
            "health": 22.5,
            "admin": 54.8,
            "debt": 36.8
          }
        },
        "2022-23": {
          "population": 314500,
          "revenues": 478.6,
          "expenditures": 482.8,
          "byFunction": {
            "police": 97.8,
            "fire": 59.2,
            "streets": 41.2,
            "parks": 43.3,
            "library": 18.8,
            "housing": 49.8,
            "sanitation": 53.8,
            "health": 24.1,
            "admin": 57.2,
            "debt": 37.6
          }
        },
        "2023-24": {
          "population": 314000,
          "revenues": 521.6,
          "expenditures": 501.4,
          "byFunction": {
            "police": 99.4,
            "fire": 62.7,
            "streets": 42.6,
            "parks": 44.5,
            "library": 19.5,
            "housing": 53.3,
            "sanitation": 55.8,
            "health": 25.3,
            "admin": 58.5,
            "debt": 39.8
          }
        }
      }
    },
    "santa-ana": {
      "name": "Santa Ana",
      "county": "Orange",
      "years": {
        "2021-22": {
          "population": 310600,
          "revenues": 406.2,
          "expenditures": 417.9,
          "byFunction": {
            "police": 111.4,
            "fire": 48.9,
            "streets": 53.4,
            "parks": 34.3,
            "library": 13.8,
            "housing": 39.8,
            "sanitation": 45.4,
            "health": 12.2,
            "admin": 32.9,
            "debt": 25.8
          }
        },
        "2022-23": {
          "population": 310300,
          "revenues": 417.2,
          "expenditures": 434.5,
          "byFunction": {
            "police": 115.5,
            "fire": 50.9,
            "streets": 56.7,
            "parks": 35.5,
            "library": 14.6,
            "housing": 39.9,
            "sanitation": 48.9,
            "health": 12.9,
            "admin": 33.8,
            "debt": 25.8
          }
        },
        "2023-24": {
          "population": 310000,
          "revenues": 466.3,
          "expenditures": 463.9,
          "byFunction": {
            "police": 126.3,
            "fire": 55.2,
            "streets": 58.5,
            "parks": 37.4,
            "library": 15.3,
            "housing": 42.5,
            "sanitation": 51.9,
            "health": 13.2,
            "admin": 36.1,
            "debt": 27.5
          }
        }
      }
    },
    "chula-vista": {
      "name": "Chula Vista",
      "county": "San Diego",
      "years": {
        "2021-22": {
          "population": 278900,
          "revenues": 321.9,
          "expenditures": 314.3,
          "byFunction": {
            "police": 79.7,
            "fire": 37.1,
            "streets": 40.1,
            "parks": 17.2,
            "library": 12.3,
            "housing": 27.7,
            "sanitation": 38.5,
            "health": 13.1,
            "admin": 30.1,
            "debt": 18.5
          }
        },
        "2022-23": {
          "population": 278900,
          "revenues": 309.6,
          "expenditures": 323.1,
          "byFunction": {
            "police": 78.3,
            "fire": 39.3,
            "streets": 41.5,
            "parks": 18.1,
            "library": 13,
            "housing": 27.7,
            "sanitation": 40.8,
            "health": 13.5,
            "admin": 31.5,
            "debt": 19.4
          }
        },
        "2023-24": {
          "population": 279000,
          "revenues": 324.2,
          "expenditures": 334.9,
          "byFunction": {
            "police": 82.7,
            "fire": 40.7,
            "streets": 42.2,
            "parks": 18.1,
            "library": 13.2,
            "housing": 29.9,
            "sanitation": 42.7,
            "health": 13.7,
            "admin": 31.1,
            "debt": 20.6
          }
        }
      }
    },
    "fremont": {
      "name": "Fremont",
      "county": "Alameda",
      "years": {
        "2021-22": {
          "population": 224700,
          "revenues": 284,
          "expenditures": 289.1,
          "byFunction": {
            "police": 68.8,
            "fire": 41.9,
            "streets": 39.2,
            "parks": 17,
            "library": 12.9,
            "housing": 20,
            "sanitation": 35.3,
            "health": 12.2,
            "admin": 26.9,
            "debt": 14.9
          }
        },
        "2022-23": {
          "population": 225400,
          "revenues": 316.9,
          "expenditures": 299.5,
          "byFunction": {
            "police": 70.4,
            "fire": 43.4,
            "streets": 40.7,
            "parks": 17.5,
            "library": 13.9,
            "housing": 21.4,
            "sanitation": 36.2,
            "health": 12.3,
            "admin": 27.9,
            "debt": 15.8
          }
        },
        "2023-24": {
          "population": 226000,
          "revenues": 340.2,
          "expenditures": 316.9,
          "byFunction": {
            "police": 75.2,
            "fire": 46.5,
            "streets": 43.5,
            "parks": 18.6,
            "library": 14.3,
            "housing": 21.6,
            "sanitation": 38.4,
            "health": 13.3,
            "admin": 28.5,
            "debt": 17
          }
        }
      }
    },
    "san-bernardino": {
      "name": "San Bernardino",
      "county": "San Bernardino",
      "years": {
        "2021-22": {
          "population": 223600,
          "revenues": 267.2,
          "expenditures": 255.2,
          "byFunction": {
            "police": 43.9,
            "fire": 38.1,
            "streets": 32,
            "parks": 15.4,
            "library": 7,
            "housing": 26.4,
            "sanitation": 35.9,
            "health": 10.4,
            "admin": 31.4,
            "debt": 14.7
          }
        },
        "2022-23": {
          "population": 223300,
          "revenues": 273.7,
          "expenditures": 262.3,
          "byFunction": {
            "police": 45.3,
            "fire": 40.1,
            "streets": 31.9,
            "parks": 15.4,
            "library": 7.1,
            "housing": 27.1,
            "sanitation": 37.1,
            "health": 11,
            "admin": 31.8,
            "debt": 15.5
          }
        },
        "2023-24": {
          "population": 223000,
          "revenues": 296.9,
          "expenditures": 278.4,
          "byFunction": {
            "police": 48.7,
            "fire": 42.3,
            "streets": 34.2,
            "parks": 16,
            "library": 7.5,
            "housing": 28,
            "sanitation": 40.2,
            "health": 11.2,
            "admin": 34.2,
            "debt": 16.1
          }
        }
      }
    },
    "modesto": {
      "name": "Modesto",
      "county": "Stanislaus",
      "years": {
        "2021-22": {
          "population": 218400,
          "revenues": 272.1,
          "expenditures": 267.8,
          "byFunction": {
            "police": 56.6,
            "fire": 35,
            "streets": 37.5,
            "parks": 23.7,
            "library": 12.2,
            "housing": 25.4,
            "sanitation": 24,
            "health": 8.8,
            "admin": 30.1,
            "debt": 14.5
          }
        },
        "2022-23": {
          "population": 218200,
          "revenues": 292.7,
          "expenditures": 281.4,
          "byFunction": {
            "police": 58.6,
            "fire": 38.7,
            "streets": 39.8,
            "parks": 24.5,
            "library": 12.4,
            "housing": 27.1,
            "sanitation": 25.3,
            "health": 9.4,
            "admin": 30.1,
            "debt": 15.5
          }
        },
        "2023-24": {
          "population": 218000,
          "revenues": 309.5,
          "expenditures": 292.1,
          "byFunction": {
            "police": 59.6,
            "fire": 39.8,
            "streets": 42.1,
            "parks": 25,
            "library": 12.9,
            "housing": 27.8,
            "sanitation": 27.5,
            "health": 9.6,
            "admin": 31.6,
            "debt": 16.2
          }
        }
      }
    },
    "santa-barbara": {
      "name": "Santa Barbara",
      "county": "Santa Barbara",
      "years": {
        "2021-22": {
          "population": 87600,
          "revenues": 198.9,
          "expenditures": 202.7,
          "byFunction": {
            "police": 35.2,
            "fire": 28.4,
            "streets": 21.9,
            "parks": 15,
            "library": 5.4,
            "housing": 22.5,
            "sanitation": 23.6,
            "health": 12.8,
            "admin": 28.1,
            "debt": 9.8
          }
        },
        "2022-23": {
          "population": 87800,
          "revenues": 208,
          "expenditures": 208.8,
          "byFunction": {
            "police": 36.9,
            "fire": 29.3,
            "streets": 22.9,
            "parks": 15.1,
            "library": 5.6,
            "housing": 23.5,
            "sanitation": 24,
            "health": 12.8,
            "admin": 28.5,
            "debt": 10.2
          }
        },
        "2023-24": {
          "population": 88000,
          "revenues": 232,
          "expenditures": 218.7,
          "byFunction": {
            "police": 38.4,
            "fire": 30.7,
            "streets": 24.9,
            "parks": 15.8,
            "library": 6.1,
            "housing": 24.3,
            "sanitation": 24.4,
            "health": 13.4,
            "admin": 30.1,
            "debt": 10.6
          }
        }
      }
    }
  }
};
