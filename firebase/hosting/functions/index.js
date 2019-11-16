const admin = require('firebase-admin');
const functions = require('firebase-functions');
const express = require('express');
const engines = require('consolidate');

// Configure Firestore
admin.initializeApp(functions.config().firebase);

let db = admin.firestore();



// Configure Express
const app = express();
app.engine('hbs', engines.handlebars);
app.set('views', './views');
app.set('view engine', 'hbs');


// Express Function
app.get('/onboard/*', (request, response) => {
    const sessionID = request.url.split('/')[2];

    // Check for Session ID in Firestore
    let sessionReference = db.collection('dev').doc(sessionID);
    console.log(sessionReference);
    let sessionDoc = sessionReference.get()
        .then(doc => {
            // eslint-disable-next-line promise/always-return
            if (!doc.exists) {
                response.redirect('/?invalid');
            } else {
                response.render('onboarding', {id: sessionID});
            }
        })
        .catch(error =>{
            console.log("Session ID " + sessionID + " returned an error:");
            console.log(error);
            response.redirect('/?serverError');
        });
});

// Firebase Cloud Function Declaration
exports.onboarding = functions.https.onRequest(app)