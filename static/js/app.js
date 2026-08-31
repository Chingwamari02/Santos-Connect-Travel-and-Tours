const menu=document.getElementById("menu"), nav=document.getElementById("nav");
if(menu) menu.onclick=()=>nav.classList.toggle("open");
document.querySelectorAll(".story").forEach(s=>s.onclick=()=>{
  const viewer=document.getElementById("viewer"), box=document.getElementById("view");
  box.innerHTML="";
  if(s.dataset.type==="image"){const i=document.createElement("img");i.src=s.dataset.file;box.appendChild(i)}
  else {const v=document.createElement("video");v.src=s.dataset.file;v.controls=true;v.autoplay=true;box.appendChild(v)}
  viewer.classList.add("show");
});
const close=document.getElementById("close");
if(close) close.onclick=()=>document.getElementById("viewer").classList.remove("show");
document.getElementById("year").textContent=new Date().getFullYear();
