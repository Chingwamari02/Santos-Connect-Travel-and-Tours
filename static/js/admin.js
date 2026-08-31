const input=document.getElementById("media"), preview=document.getElementById("preview"), check=document.getElementById("check"), duration=document.getElementById("duration");
input.addEventListener("change",()=>{
  const f=input.files[0]; if(!f)return;
  preview.innerHTML=""; check.textContent="";
  if(f.type.startsWith("image/")){
    if(f.size>2*1024*1024){check.textContent="❌ Image exceeds 2 MB.";check.style.color="crimson";return}
    const img=document.createElement("img");img.src=URL.createObjectURL(f);img.style="max-width:220px;border-radius:10px;margin:10px 0";preview.appendChild(img);
    check.textContent="✓ Image ready. Maximum size: 2 MB.";check.style.color="green";
  } else if(f.type.startsWith("video/")){
    const v=document.createElement("video");v.src=URL.createObjectURL(f);v.controls=true;v.style="max-width:300px;border-radius:10px;margin:10px 0";preview.appendChild(v);
    v.onloadedmetadata=()=>{duration.value=v.duration.toFixed(2);if(v.duration>30){check.textContent="❌ Video is "+v.duration.toFixed(1)+"s. Maximum is 30 seconds.";check.style.color="crimson"}else{check.textContent="✓ Video is "+v.duration.toFixed(1)+"s. Ready.";check.style.color="green"}};
  }
});
document.getElementById("uploadForm").addEventListener("submit",e=>{if(check.textContent.startsWith("❌"))e.preventDefault()});
