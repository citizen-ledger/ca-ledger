/* ============================================================
   THE CALIFORNIA LEDGER — DATA FILE
   ------------------------------------------------------------
   STATUS: SAMPLE DATA. Figures are illustrative approximations
   of the shape of recent California enacted budgets, hand-built
   so the interface is fully functional before the real pipeline
   runs. Do not cite these numbers.

   To replace with real data, run: pipeline/fetch_state_data.py
   (see README.md). That script regenerates this file in the
   exact same schema, and sets meta.source to the live dataset.

   All dollar amounts are in BILLIONS.
   Fund keys: gf = General Fund, sp = Special Funds,
              bd = Bond Funds,   fed = Federal Funds
   ============================================================ */

window.CA_LEDGER_DATA = {
  meta: {
    source: "SAMPLE",
    sourceLabel: "Illustrative sample data — not official figures",
    generated: "2026-07-08",
    population: { "2023-24": 38.97, "2024-25": 39.13 } // millions
  },

  years: ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"],

  // State-funds totals by year (GF + Special + Bond), billions
  trend: {
    "2019-20": { state: 215.0, federal: 105.0 },
    "2020-21": { state: 202.1, federal: 168.0 },
    "2021-22": { state: 262.5, federal: 176.0 },
    "2022-23": { state: 308.0, federal: 162.0 },
    "2023-24": { state: 310.8, federal: 158.5 },
    "2024-25": { state: 297.9, federal: 166.0 }
  },

  budgets: {
    "2024-25": {
      agencies: [
        {
          id: "hhs", name: "Health & Human Services",
          gf: 72.0, sp: 27.9, bd: 0.1, fed: 159.8,
          departments: [
            { name: "Health Care Services (Medi-Cal)", gf: 35.2, sp: 18.4, bd: 0, fed: 121.0 },
            { name: "Social Services", gf: 16.1, sp: 1.1, bd: 0, fed: 26.8 },
            { name: "Developmental Services", gf: 8.9, sp: 0.4, bd: 0, fed: 5.6 },
            { name: "State Hospitals", gf: 3.5, sp: 0.2, bd: 0, fed: 0.1 },
            { name: "Public Health", gf: 1.9, sp: 3.1, bd: 0, fed: 3.4 },
            { name: "Other HHS departments", gf: 6.4, sp: 4.7, bd: 0.1, fed: 2.9 }
          ]
        },
        {
          id: "k12", name: "K-12 Education",
          gf: 78.6, sp: 0.1, bd: 3.2, fed: 8.1,
          departments: [
            { name: "Local school apportionments (LCFF)", gf: 64.4, sp: 0, bd: 0, fed: 0 },
            { name: "Special education", gf: 5.1, sp: 0, bd: 0, fed: 1.4 },
            { name: "Child nutrition & meals", gf: 1.9, sp: 0, bd: 0, fed: 3.2 },
            { name: "School facilities", gf: 0.4, sp: 0, bd: 3.2, fed: 0 },
            { name: "Other K-12 programs", gf: 6.8, sp: 0.1, bd: 0, fed: 3.5 }
          ]
        },
        {
          id: "highered", name: "Higher Education",
          gf: 20.9, sp: 3.1, bd: 0.6, fed: 4.0,
          departments: [
            { name: "University of California", gf: 5.0, sp: 0.3, bd: 0.2, fed: 1.8 },
            { name: "California State University", gf: 5.3, sp: 0.2, bd: 0.2, fed: 1.1 },
            { name: "Community Colleges", gf: 8.4, sp: 0.4, bd: 0.2, fed: 0.9 },
            { name: "Student Aid Commission", gf: 2.2, sp: 2.2, bd: 0, fed: 0.2 }
          ]
        },
        {
          id: "corrections", name: "Corrections & Rehabilitation",
          gf: 13.6, sp: 0.6, bd: 0, fed: 0.1,
          departments: [
            { name: "Adult institutions & operations", gf: 10.2, sp: 0.3, bd: 0, fed: 0.1 },
            { name: "Health care for incarcerated people", gf: 2.6, sp: 0.1, bd: 0, fed: 0 },
            { name: "Parole & rehabilitation programs", gf: 0.8, sp: 0.2, bd: 0, fed: 0 }
          ]
        },
        {
          id: "transport", name: "Transportation",
          gf: 0.7, sp: 17.3, bd: 1.1, fed: 9.2,
          departments: [
            { name: "Caltrans — highways & roads", gf: 0.2, sp: 12.6, bd: 0.4, fed: 7.5 },
            { name: "High-Speed Rail Authority", gf: 0, sp: 1.3, bd: 0.6, fed: 0.6 },
            { name: "Motor Vehicles & Highway Patrol", gf: 0.1, sp: 3.4, bd: 0, fed: 0.1 },
            { name: "Transit assistance", gf: 0.4, sp: 0, bd: 0.1, fed: 1.0 }
          ]
        },
        {
          id: "resources", name: "Natural Resources",
          gf: 4.6, sp: 4.2, bd: 1.2, fed: 0.9,
          departments: [
            { name: "CAL FIRE — fire protection", gf: 2.9, sp: 0.6, bd: 0, fed: 0.2 },
            { name: "Water Resources", gf: 0.5, sp: 1.4, bd: 0.7, fed: 0.3 },
            { name: "Parks & Recreation", gf: 0.6, sp: 0.9, bd: 0.2, fed: 0.1 },
            { name: "Fish & Wildlife, conservancies, other", gf: 0.6, sp: 1.3, bd: 0.3, fed: 0.3 }
          ]
        },
        {
          id: "epa", name: "Environmental Protection",
          gf: 1.1, sp: 4.1, bd: 0.2, fed: 0.4,
          departments: [
            { name: "Air Resources Board", gf: 0.3, sp: 2.3, bd: 0, fed: 0.1 },
            { name: "Water Boards", gf: 0.4, sp: 1.0, bd: 0.2, fed: 0.2 },
            { name: "Toxic substances, recycling, other", gf: 0.4, sp: 0.8, bd: 0, fed: 0.1 }
          ]
        },
        {
          id: "housing", name: "Business, Consumer Services & Housing",
          gf: 2.4, sp: 2.3, bd: 0.3, fed: 3.6,
          departments: [
            { name: "Housing & Community Development", gf: 1.6, sp: 0.4, bd: 0.3, fed: 2.9 },
            { name: "Homelessness programs (Cal ICH)", gf: 0.5, sp: 0, bd: 0, fed: 0.2 },
            { name: "Licensing, consumer affairs, other", gf: 0.3, sp: 1.9, bd: 0, fed: 0.5 }
          ]
        },
        {
          id: "labor", name: "Labor & Workforce Development",
          gf: 1.2, sp: 1.0, bd: 0, fed: 21.5,
          departments: [
            { name: "Employment Development (incl. UI benefits)", gf: 0.7, sp: 0.4, bd: 0, fed: 20.8 },
            { name: "Workforce development & apprenticeships", gf: 0.3, sp: 0.2, bd: 0, fed: 0.5 },
            { name: "Industrial relations", gf: 0.2, sp: 0.4, bd: 0, fed: 0.2 }
          ]
        },
        {
          id: "govops", name: "Government Operations",
          gf: 2.7, sp: 1.6, bd: 0, fed: 0.8,
          departments: [
            { name: "Technology, HR & general services", gf: 1.2, sp: 1.0, bd: 0, fed: 0.3 },
            { name: "Tax administration (FTB, CDTFA)", gf: 1.3, sp: 0.4, bd: 0, fed: 0.1 },
            { name: "Emergency procurement & other", gf: 0.2, sp: 0.2, bd: 0, fed: 0.4 }
          ]
        },
        {
          id: "ljE", name: "Legislative, Judicial & Executive",
          gf: 9.4, sp: 3.6, bd: 0.1, fed: 1.2,
          departments: [
            { name: "Judicial branch & courts", gf: 3.9, sp: 1.5, bd: 0, fed: 0.1 },
            { name: "Legislature", gf: 0.5, sp: 0, bd: 0, fed: 0 },
            { name: "Justice (Attorney General)", gf: 1.1, sp: 0.6, bd: 0, fed: 0.2 },
            { name: "Emergency Services (Cal OES)", gf: 2.4, sp: 0.3, bd: 0, fed: 0.8 },
            { name: "Elections, constitutional offices, other", gf: 1.5, sp: 1.2, bd: 0.1, fed: 0.1 }
          ]
        },
        {
          id: "general", name: "General Government",
          gf: 7.8, sp: 6.1, bd: 0.1, fed: 0.9,
          departments: [
            { name: "Debt service on bonds", gf: 5.2, sp: 0.7, bd: 0, fed: 0 },
            { name: "Pension & retiree health contributions", gf: 1.4, sp: 0.9, bd: 0, fed: 0 },
            { name: "Local government subventions", gf: 0.6, sp: 3.1, bd: 0, fed: 0.2 },
            { name: "Reserves, settlements & other", gf: 0.6, sp: 1.4, bd: 0.1, fed: 0.7 }
          ]
        }
      ]
    },

    "2023-24": {
      agencies: [
        { id: "hhs", name: "Health & Human Services", gf: 70.1, sp: 26.8, bd: 0.1, fed: 152.3,
          departments: [
            { name: "Health Care Services (Medi-Cal)", gf: 33.9, sp: 17.7, bd: 0, fed: 114.9 },
            { name: "Social Services", gf: 15.6, sp: 1.0, bd: 0, fed: 25.9 },
            { name: "Developmental Services", gf: 8.2, sp: 0.4, bd: 0, fed: 5.2 },
            { name: "State Hospitals", gf: 3.4, sp: 0.2, bd: 0, fed: 0.1 },
            { name: "Public Health", gf: 2.1, sp: 3.0, bd: 0, fed: 3.6 },
            { name: "Other HHS departments", gf: 6.9, sp: 4.5, bd: 0.1, fed: 2.6 } ] },
        { id: "k12", name: "K-12 Education", gf: 76.9, sp: 0.1, bd: 3.6, fed: 9.0,
          departments: [
            { name: "Local school apportionments (LCFF)", gf: 62.8, sp: 0, bd: 0, fed: 0 },
            { name: "Special education", gf: 4.9, sp: 0, bd: 0, fed: 1.4 },
            { name: "Child nutrition & meals", gf: 1.8, sp: 0, bd: 0, fed: 3.1 },
            { name: "School facilities", gf: 0.5, sp: 0, bd: 3.6, fed: 0 },
            { name: "Other K-12 programs", gf: 6.9, sp: 0.1, bd: 0, fed: 4.5 } ] },
        { id: "highered", name: "Higher Education", gf: 21.5, sp: 3.0, bd: 0.7, fed: 3.9,
          departments: [
            { name: "University of California", gf: 5.2, sp: 0.3, bd: 0.2, fed: 1.7 },
            { name: "California State University", gf: 5.5, sp: 0.2, bd: 0.3, fed: 1.1 },
            { name: "Community Colleges", gf: 8.5, sp: 0.4, bd: 0.2, fed: 0.9 },
            { name: "Student Aid Commission", gf: 2.3, sp: 2.1, bd: 0, fed: 0.2 } ] },
        { id: "corrections", name: "Corrections & Rehabilitation", gf: 14.1, sp: 0.6, bd: 0, fed: 0.1,
          departments: [
            { name: "Adult institutions & operations", gf: 10.6, sp: 0.3, bd: 0, fed: 0.1 },
            { name: "Health care for incarcerated people", gf: 2.7, sp: 0.1, bd: 0, fed: 0 },
            { name: "Parole & rehabilitation programs", gf: 0.8, sp: 0.2, bd: 0, fed: 0 } ] },
        { id: "transport", name: "Transportation", gf: 1.2, sp: 16.8, bd: 1.3, fed: 8.7,
          departments: [
            { name: "Caltrans — highways & roads", gf: 0.5, sp: 12.2, bd: 0.5, fed: 7.1 },
            { name: "High-Speed Rail Authority", gf: 0, sp: 1.2, bd: 0.7, fed: 0.5 },
            { name: "Motor Vehicles & Highway Patrol", gf: 0.1, sp: 3.4, bd: 0, fed: 0.1 },
            { name: "Transit assistance", gf: 0.6, sp: 0, bd: 0.1, fed: 1.0 } ] },
        { id: "resources", name: "Natural Resources", gf: 5.4, sp: 4.0, bd: 1.4, fed: 0.9,
          departments: [
            { name: "CAL FIRE — fire protection", gf: 3.2, sp: 0.5, bd: 0, fed: 0.2 },
            { name: "Water Resources", gf: 0.7, sp: 1.3, bd: 0.8, fed: 0.3 },
            { name: "Parks & Recreation", gf: 0.7, sp: 0.9, bd: 0.3, fed: 0.1 },
            { name: "Fish & Wildlife, conservancies, other", gf: 0.8, sp: 1.3, bd: 0.3, fed: 0.3 } ] },
        { id: "epa", name: "Environmental Protection", gf: 1.5, sp: 4.0, bd: 0.2, fed: 0.4,
          departments: [
            { name: "Air Resources Board", gf: 0.5, sp: 2.2, bd: 0, fed: 0.1 },
            { name: "Water Boards", gf: 0.5, sp: 1.0, bd: 0.2, fed: 0.2 },
            { name: "Toxic substances, recycling, other", gf: 0.5, sp: 0.8, bd: 0, fed: 0.1 } ] },
        { id: "housing", name: "Business, Consumer Services & Housing", gf: 3.1, sp: 2.2, bd: 0.4, fed: 3.8,
          departments: [
            { name: "Housing & Community Development", gf: 2.1, sp: 0.4, bd: 0.4, fed: 3.0 },
            { name: "Homelessness programs (Cal ICH)", gf: 0.7, sp: 0, bd: 0, fed: 0.2 },
            { name: "Licensing, consumer affairs, other", gf: 0.3, sp: 1.8, bd: 0, fed: 0.6 } ] },
        { id: "labor", name: "Labor & Workforce Development", gf: 1.4, sp: 0.9, bd: 0, fed: 23.9,
          departments: [
            { name: "Employment Development (incl. UI benefits)", gf: 0.9, sp: 0.4, bd: 0, fed: 23.2 },
            { name: "Workforce development & apprenticeships", gf: 0.3, sp: 0.2, bd: 0, fed: 0.5 },
            { name: "Industrial relations", gf: 0.2, sp: 0.3, bd: 0, fed: 0.2 } ] },
        { id: "govops", name: "Government Operations", gf: 3.1, sp: 1.5, bd: 0, fed: 0.9,
          departments: [
            { name: "Technology, HR & general services", gf: 1.4, sp: 0.9, bd: 0, fed: 0.3 },
            { name: "Tax administration (FTB, CDTFA)", gf: 1.4, sp: 0.4, bd: 0, fed: 0.1 },
            { name: "Emergency procurement & other", gf: 0.3, sp: 0.2, bd: 0, fed: 0.5 } ] },
        { id: "ljE", name: "Legislative, Judicial & Executive", gf: 9.8, sp: 3.4, bd: 0.1, fed: 1.3,
          departments: [
            { name: "Judicial branch & courts", gf: 4.0, sp: 1.5, bd: 0, fed: 0.1 },
            { name: "Legislature", gf: 0.5, sp: 0, bd: 0, fed: 0 },
            { name: "Justice (Attorney General)", gf: 1.2, sp: 0.6, bd: 0, fed: 0.2 },
            { name: "Emergency Services (Cal OES)", gf: 2.6, sp: 0.2, bd: 0, fed: 0.9 },
            { name: "Elections, constitutional offices, other", gf: 1.5, sp: 1.1, bd: 0.1, fed: 0.1 } ] },
        { id: "general", name: "General Government", gf: 8.9, sp: 5.8, bd: 0.1, fed: 1.0,
          departments: [
            { name: "Debt service on bonds", gf: 5.0, sp: 0.7, bd: 0, fed: 0 },
            { name: "Pension & retiree health contributions", gf: 1.3, sp: 0.9, bd: 0, fed: 0 },
            { name: "Local government subventions", gf: 0.9, sp: 3.0, bd: 0, fed: 0.2 },
            { name: "Reserves, settlements & other", gf: 1.7, sp: 1.2, bd: 0.1, fed: 0.8 } ] }
      ]
    }
  }
};
