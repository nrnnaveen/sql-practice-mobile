var canvas = document.getElementById("matrix");
var ctx = canvas.getContext("2d");

canvas.height = window.innerHeight;
canvas.width = window.innerWidth;

var letters = "01";
letters = letters.split("");

var fontSize = 14;
var columns = canvas.width / fontSize;

var drops = [];

for(var x = 0; x < columns; x++)
drops[x] = 1;

function draw(){

ctx.fillStyle = "rgba(0, 0, 0, 0.05)";
ctx.fillRect(0,0,canvas.width,canvas.height);

ctx.fillStyle = "#0f0";
ctx.font = fontSize + "px monospace";

for(var i = 0; i < drops.length; i++){

var text = letters[Math.floor(Math.random()*letters.length)];

ctx.fillText(text,i*fontSize,drops[i]*fontSize);

if(drops[i]*fontSize > canvas.height && Math.random() > 0.975)
drops[i] = 0;

drops[i]++;

}

}

setInterval(draw,33);
