import { mount } from 'svelte'
import './app.css'
import App from './App.svelte'

const app = mount(App, {
  target: document.getElementById('app')!,
});

export default app;

/* 
 * Most of the below functionality (unless dealing with the API) will be taken from my (Prince's) Homework 1 Submission. 
 */

/* 
 * **Sets Today's Date** (Carryover from Homework 1)
 * Code to dynamically set the date (gets the element at "current-date").
 * Referred to ChatGPT on the specific location it should be placed in the code. 
 * I initially planned on having a separate script.js file, but figured that scripting within the same HTML file would likely be sufficient due to the relative simplicity.
 */

// Gets the element with the date (using the id "current-date").
const dateElement = document.getElementById("current-date");
if(dateElement) 
{
  /*
    * Saves the date format to be [Weekday],[Month] [Day], [Year]. Matches that of the actual New York Times front page. 
    * Since this is TypeScript instead of JavaScript, I had to specify the type of the options object as "const" to ensure the values are treated as literals.
    */
  const options = 
  {
    weekday : "long" as const, 
    year: "numeric" as const, 
    month: "long" as const, 
    day: "numeric" as const
  };
  const today = new Date().toLocaleDateString("en-US", options);
  dateElement.textContent = today;
}

/*
 * **Stock Ticker Functionality** (Carryover from Homework 1)
 * A constant array of stock data, assigned it a name, symbol, percent change, and whether it is up or down. 
 * I decided to do it this way instead of adding logic to figure out whether it was up or down based on the percent value since it was simpler this way.
 */
// Altered the values of the stock changes to reflect today (May 1, 2024) in the stock market.
// Also added the Timberwolves, and changed the Lakers to be down 100% since we lost the playoff series.
const stocks = 
[
  { name: "S&P 500", symbol: "SPY", change: "+0.63%", up: true },
  { name: "NASDAQ", symbol: "NDAQ", change: "+1.52%", up: true },
  { name: "Timberwolves", symbol: "MIN", change: "+100%", up: true }, // Timberwolves are down 100% since we lost the playoff series
  { name: "Lakers", symbol: "LAL", change: "-100%", up: false }, // While the entire stock market was down today, the Lakers are up since we got Luka
  { name: "DOW", symbol: "DJI", change: "+0.21%", up: true }
];

// Selects the stock ticker element
const ticker = document.getElementById("stock-ticker");

// Sets the initial index to 0, or the first element in the array (S&P 500)
let index = 0;

// Function updates the contents of the ticker that's displayed
function updateTicker() 
{
  if(!ticker)
    {
      // If the ticker element doesn't exist, exit the function
      return;
    }
    //Fades out the current content
    ticker.classList.remove("fade-in");
    ticker.classList.add("fade-out");

    // Waits until the fade-out transition is complete before updating the content
    setTimeout(() => 
    {
        // Sets "stock" to the current index
        const stock = stocks[index];
        // If the stock is up (i.e. if the boolean value is set to true) it uses the up arrow. Otherwise, it uses the down arrow.
        const arrow = stock.up ? "▲" : "▼";
        // Again, if the stock is up, it uses the stock-up class, which is styled in the CSS to be green. Otherwise, it uses stock-down, which is red.
        const colorClass = stock.up ? "stock-up" : "stock-down";

        // Updates the ticker's HTML with the name of the stock, the arrow indicating whether it's up or down, and the percent change.
        ticker.innerHTML = `
            <span class="stock-name">${stock.name}</span>
            <span class="${colorClass}">${arrow} ${stock.change}</span>
        `;

        // Fades in the new content
        ticker.classList.remove("fade-out");
        ticker.classList.add("fade-in");

        // Cycle to the next stock. I use a modulus to loop back through the array so that it doesn't go out of bounds.
        index = (index + 1) % stocks.length;
    }, 500); // Waits 500 milliseconds 
}
  // Initial display
  updateTicker();

  // Rotate every 5 seconds
  setInterval(updateTicker, 5000);

// import { mount } from 'svelte'
// import './app.css'
// import App from './App.svelte'

// const app = mount(App, {
//   target: document.getElementById('app')!,
// })

// export default app
