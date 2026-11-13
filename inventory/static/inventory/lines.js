const lines = document.querySelector("#lines");
const total = document.querySelector("#id_form-TOTAL_FORMS");
const add = document.querySelector("#add-line");
const remove = document.querySelector("#remove-line");
const template = document.querySelector("#line-template");

function updateControls() {
    add.disabled = lines.children.length >= 50;
    remove.disabled = lines.children.length <= 1;
    total.value = lines.children.length;
}

add.addEventListener("click", () => {
    lines.insertAdjacentHTML("beforeend", template.innerHTML.replaceAll("__prefix__", total.value));
    updateControls();
    lines.lastElementChild.querySelector("select").focus();
});

remove.addEventListener("click", () => {
    lines.lastElementChild.remove();
    updateControls();
});

updateControls();