document.addEventListener("DOMContentLoaded",function(){var e=document.getElementById("chatinput-form"),t=document.querySelector("#chat-input"),o=document.querySelector("#conversation-list"),a=document.getElementsByClassName("contacts-link"),i=document.querySelector(".chat-body"),n=document.querySelector("[data-close]"),s=document.getElementsByClassName("username"),d=document.getElementsByClassName("user-avatar"),r=document.getElementsByClassName("chat-item"),c=document.getElementById("active-chat-user"),l=1,m=["Hi","Hello !","Hey :)","How do you do?","Are you there?","I am doing good :)","Hi can we meet today?","How are you?","May I know your good name?","I am from codescandy","Where are you from?","What's Up!"],u=(Array.from(a).forEach(function(e){e.addEventListener("click",function(e){i.classList.add("chat-body-visible")})}),n.addEventListener("click",function(e){i.classList.remove("chat-body-visible")}),document.body.contains(n)&&n.addEventListener("click",function(e){i.classList.remove("chat-body-visible")}),Array.from(r).forEach(function(r){r.addEventListener("click",function(e){var t=r.querySelector("img").parentNode.className,o=r.querySelector("img").src,a=r.querySelector("h5").innerHTML,i=r.querySelector("small"),n=t.split(" ");n=(n=n[n.length-1].split("-"))[1].slice(0,1).toUpperCase()+n[1].slice(1).toLowerCase(),c.querySelector("h3").innerHTML=a,c.querySelector("img").src=o,c.querySelector("img").parentNode.className=t,c.querySelector("p").innerHTML=n,null!==i&&i.nextElementSibling&&i.parentElement.removeChild(i.nextElementSibling),Array.from(s).forEach(function(e){e.innerHTML=a}),Array.from(d).forEach(function(e){e.src=o})})}),document.body.contains(e)&&e.addEventListener("submit",function(e){e.preventDefault();e=(e=new Date).getHours()+":"+e.getMinutes();o.insertAdjacentHTML("beforeend",'<div class="d-flex justify-content-end mb-4" id="chat-item-'+l+`">
      <div class="d-flex">
          <div class=" me-3 text-end">
              <small>`+e+`</small>
              <div class="d-flex">
                  <div class="me-2 mt-2">
                      <div class="dropdown dropstart">
                          <a class="btn btn-ghost btn-icon btn-sm rounded-circle" href="#!" role="button"
                              id="dropdownMenuLinkTwo" data-bs-toggle="dropdown"
                              aria-haspopup="true" aria-expanded="false">
                              <i class="ti ti-dots-vertical"></i>
                          </a>
                          <div class="dropdown-menu" aria-labelledby="dropdownMenuLinkTwo">
                              <a class="dropdown-item" href="#!">
                                <i class="dropdown-item-icon ti ti-copy"></i>Copy</a>
                              <a class="dropdown-item" href="#!">
                                <i class="dropdown-item-icon ti ti-edit"></i> Edit</a>
                              <a class="dropdown-item" href="#!">
                                <i class="dropdown-item-icon ti ti-corner-up-right" ></i>Reply</a>
                              <a class="dropdown-item" href="#!">
                                <i class=" dropdown-item-icon ti ti-corner-up-left" ></i>Forward</a>
                              <a class="dropdown-item" href="#!">
                                <i class="dropdown-item-icon ti ti-star" ></i>Favourite</a>
                              <a class="dropdown-item" href="#!">
                                <i class="dropdown-item-icon ti ti-trash" ></i>Delete
                              </a>
                          </div>
                      </div>
                  </div>
                  <div
                      class="card mt-2 bg-primary-subtle text-primary-emphasis border-0">
                      <div class="card-body text-start p-3">
                          <p class="mb-0">`+t.value+`</p>
                      </div>
                  </div>
              </div>
          </div>
          <img src="../assets/images/avatar/avatar-11.jpg" alt="Image" class="rounded-circle avatar-md" />
      </div>
  </div>`),o.scrollTop=o.scrollHeight,u(),l++}),function(){newRandomMsg=m[Math.floor(Math.random()*m.length)],t.value=newRandomMsg});u()});