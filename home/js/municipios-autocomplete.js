(function () {
    "use strict";

    function initMunicipioAutocomplete(inputId, listId, opts) {
        var input = document.getElementById(inputId);
        var list = document.getElementById(listId);
        if (!input || !list) return;

        opts = opts || {};
        var timer = null;
        var activeIndex = -1;
        var currentItems = [];

        function fecharLista() {
            list.innerHTML = "";
            list.classList.add("hidden");
            input.setAttribute("aria-expanded", "false");
            activeIndex = -1;
        }

        function selecionarItem(valor) {
            input.value = valor;
            input.dataset.municipioValido = valor;
            input.setCustomValidity("");
            fecharLista();
            if (typeof opts.onSelect === "function") {
                opts.onSelect(valor);
            }
        }

        function atualizarDestaque() {
            var opcoes = list.querySelectorAll("[role='option']");
            for (var i = 0; i < opcoes.length; i++) {
                if (i === activeIndex) {
                    opcoes[i].classList.add("is-active");
                    opcoes[i].setAttribute("aria-selected", "true");
                } else {
                    opcoes[i].classList.remove("is-active");
                    opcoes[i].setAttribute("aria-selected", "false");
                }
            }
        }

        function renderizarLista(itens) {
            currentItems = itens || [];
            list.innerHTML = "";
            activeIndex = -1;

            if (!currentItems.length) {
                var vazio = document.createElement("div");
                vazio.className = "autocomplete-empty";
                vazio.textContent = "Nenhum município encontrado. Digite outro nome.";
                list.appendChild(vazio);
                list.classList.remove("hidden");
                input.setAttribute("aria-expanded", "true");
                return;
            }

            currentItems.forEach(function (item, idx) {
                var btn = document.createElement("button");
                btn.type = "button";
                btn.setAttribute("role", "option");
                btn.setAttribute("aria-selected", "false");
                btn.className = "autocomplete-option";
                btn.textContent = item;
                btn.addEventListener("mousedown", function (e) {
                    e.preventDefault();
                    selecionarItem(item);
                });
                btn.addEventListener("mouseenter", function () {
                    activeIndex = idx;
                    atualizarDestaque();
                });
                list.appendChild(btn);
            });

            list.classList.remove("hidden");
            input.setAttribute("aria-expanded", "true");
        }

        input.addEventListener("input", function () {
            var q = input.value.trim();
            if (opts.requireSelection) {
                input.dataset.municipioValido = "";
            }
            clearTimeout(timer);
            if (q.length < 2) {
                fecharLista();
                return;
            }
            timer = setTimeout(function () {
                fetch("/api/municipios?q=" + encodeURIComponent(q) + "&limite=10")
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        renderizarLista(data.municipios || []);
                    })
                    .catch(function () {
                        fecharLista();
                    });
            }, 200);
        });

        input.addEventListener("keydown", function (e) {
            if (list.classList.contains("hidden") || !currentItems.length) return;
            if (e.key === "ArrowDown") {
                e.preventDefault();
                activeIndex = (activeIndex + 1) % currentItems.length;
                atualizarDestaque();
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                activeIndex = (activeIndex - 1 + currentItems.length) % currentItems.length;
                atualizarDestaque();
            } else if (e.key === "Enter" && activeIndex >= 0) {
                e.preventDefault();
                selecionarItem(currentItems[activeIndex]);
            } else if (e.key === "Escape") {
                fecharLista();
            }
        });

        input.addEventListener("blur", function () {
            setTimeout(fecharLista, 150);
        });

        if (opts.requireSelection && input.form) {
            input.form.addEventListener("submit", function (e) {
                var val = input.value.trim();
                if (!val || val.indexOf(" - ") === -1) {
                    e.preventDefault();
                    input.setCustomValidity("Selecione um município brasileiro válido na lista (ex.: Araraquara - SP).");
                    input.reportValidity();
                    return;
                }
                input.setCustomValidity("");
            });
        }
    }

    window.ProtejaMunicipios = { init: initMunicipioAutocomplete };
})();
