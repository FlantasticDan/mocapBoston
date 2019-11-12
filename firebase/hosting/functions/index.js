const functions = require('firebase-functions');
const express = require('express');
const engines = require('consolidate');

// exports.onboarding = functions.https.onRequest((req, res) => {
//     const source = req.url;
//     const id = source.split('/')[2];
//     res.status(200).send(`<!doctype html>
//       <head>
//         <title>Onboarding</title>
//       </head>
//       <body>
//         <h1>${id}</h1>
//       </body>
//     </html>`);
//   });


// Configure Express
const app = express();
app.engine('hbs', engines.handlebars);
app.set('views', './views');
app.set('view engine', 'hbs');


// Express Function
app.get('/onboard/*', (request, response) => {
    const onboardID = request.url.split('/')[2]
    response.render('onboarding', {id: onboardID})
});

// Firebase Cloud Function Declaration
exports.onboarding = functions.https.onRequest(app)