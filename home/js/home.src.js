/**
 * PROTEJAJÁ // SCRIPTS CLIENT-SIDE OTIMIZADOS
 * Performance Lighthouse 100% - Sem tarefas longas na thread principal
 */
document.addEventListener("DOMContentLoaded", () => {
    // 1. AUTO-DISMISS DE ALERTAS FLASH DO SISTEMA
    document.querySelectorAll(".alert").forEach((alerta) => {
        window.setTimeout(() => {
            if (!alerta || !alerta.parentElement) return;
            alerta.style.transition = "opacity 0.3s ease, transform 0.3s ease";
            alerta.style.opacity = "0";
            alerta.style.transform = "translateY(-6px)";
            window.setTimeout(() => alerta.remove(), 300);
        }, 5000);
    });

    // EXECUÇÃO EM IDLE PARA MANTER A MAIN-THREAD LIVRE DURANTE O CARREGAMENTO (0ms BLOCKING)
    const agendarIdle = window.requestIdleCallback || function(cb) { setTimeout(cb, 1); };

    agendarIdle(() => {
        // 2. PREVIEW DE ANEXO DE PROVAS (IMAGEM / PDF / VÍDEO)
        const anexo = document.getElementById("anexo");
        const preview = document.getElementById("preview-anexo");

        if (anexo && preview) {
            anexo.addEventListener("change", () => {
                preview.innerHTML = "";
                preview.classList.add("hidden");

                const arquivo = anexo.files[0];
                if (!arquivo) return;

                preview.classList.remove("hidden");
                const info = document.createElement("p");
                info.className = "text-xs text-slate-400 mt-2 font-mono";

                if (arquivo.type.startsWith("image/")) {
                    const img = document.createElement("img");
                    img.src = URL.createObjectURL(arquivo);
                    img.className = "w-32 h-32 object-cover rounded-xl border border-rose-500/30 mb-2 shadow-lg";
                    preview.appendChild(img);
                    info.textContent = "[Foto] " + arquivo.name + " (" + Math.round(arquivo.size / 1024) + " KB)";
                } else if (arquivo.type.startsWith("video/")) {
                    info.textContent = "[Video] " + arquivo.name + " (" + Math.round(arquivo.size / 1024) + " KB)";
                } else {
                    info.textContent = "[Arquivo] " + arquivo.name + " (" + Math.round(arquivo.size / 1024) + " KB)";
                }

                preview.appendChild(info);
            });
        }

        // 3. CONTRATO DE DECLARAÇÃO E RESPONSABILIDADE LEGAL (SCROLL-TO-AGREE)
        const contratoScroll = document.getElementById("contratoScroll");
        const checkTermo = document.getElementById("checkTermo");
        const checkWrapper = document.getElementById("checkWrapper");
        const avisoScroll = document.getElementById("avisoScroll");
        const btnEnviarDenuncia = document.getElementById("btnEnviarDenuncia");

        if (contratoScroll && checkTermo && btnEnviarDenuncia) {
            let rolouAteOFim = false;

            contratoScroll.addEventListener("scroll", () => {
                if (rolouAteOFim) return;

                const margemErro = 15;
                const rolagemCompleta =
                    contratoScroll.scrollTop + contratoScroll.clientHeight >=
                    contratoScroll.scrollHeight - margemErro;

                if (rolagemCompleta) {
                    rolouAteOFim = true;
                    if (checkWrapper) {
                        checkWrapper.classList.remove("opacity-50", "pointer-events-none");
                    }
                    checkTermo.disabled = false;
                    if (avisoScroll) {
                        avisoScroll.innerHTML = "<strong>Leitura confirmada.</strong> Marque a caixa abaixo para liberar o envio.";
                        avisoScroll.className = "contrato-aviso-scroll text-green-400 font-semibold";
                    }
                }
            }, { passive: true });

            checkTermo.addEventListener("change", () => {
                if (checkTermo.checked && rolouAteOFim) {
                    btnEnviarDenuncia.disabled = false;
                    btnEnviarDenuncia.classList.remove("opacity-50", "cursor-not-allowed");
                    btnEnviarDenuncia.classList.add("btn-cyber-primary");
                } else {
                    btnEnviarDenuncia.disabled = true;
                    btnEnviarDenuncia.classList.add("opacity-50", "cursor-not-allowed");
                    btnEnviarDenuncia.classList.remove("btn-cyber-primary");
                }
            });
        }

        // 4. LOCALIZAÇÃO, AUTOCOMPLETE DE CIDADE & BUSCA DE CEP (SP)
        const cepInput = document.getElementById("cep");
        const cidadeSelect = document.getElementById("cidade");
        const campoOutraCidade = document.getElementById("campoOutraCidade");
        const cidadeOutraInput = document.getElementById("cidade_outra");
        const bairroInput = document.getElementById("bairro");
        const logradouroInput = document.getElementById("logradouro");

        if (cidadeSelect && campoOutraCidade) {
            cidadeSelect.addEventListener("change", () => {
                if (cidadeSelect.value === "Outra Cidade (SP)") {
                    campoOutraCidade.classList.remove("hidden");
                    if (cidadeOutraInput) cidadeOutraInput.required = true;
                } else {
                    campoOutraCidade.classList.add("hidden");
                    if (cidadeOutraInput) {
                        cidadeOutraInput.required = false;
                        cidadeOutraInput.value = "";
                    }
                }
            });
        }

        const cidadeDenunciaSelect = document.getElementById("cidadeDenuncia");
        const campoOutraCidadeDenuncia = document.getElementById("campoOutraCidadeDenuncia");
        const cidadeOutraDenunciaInput = document.getElementById("cidade_outra_denuncia");

        if (cidadeDenunciaSelect && campoOutraCidadeDenuncia) {
            cidadeDenunciaSelect.addEventListener("change", () => {
                if (cidadeDenunciaSelect.value === "Outra Cidade (SP)") {
                    campoOutraCidadeDenuncia.classList.remove("hidden");
                    if (cidadeOutraDenunciaInput) cidadeOutraDenunciaInput.required = true;
                } else {
                    campoOutraCidadeDenuncia.classList.add("hidden");
                    if (cidadeOutraDenunciaInput) {
                        cidadeOutraDenunciaInput.required = false;
                        cidadeOutraDenunciaInput.value = "";
                    }
                }
            });
        }

        if (cepInput) {
            cepInput.addEventListener("input", async (e) => {
                let valor = e.target.value.replace(/\D/g, "");
                if (valor.length > 5) {
                    e.target.value = valor.slice(0, 5) + "-" + valor.slice(5, 8);
                } else {
                    e.target.value = valor;
                }

                if (valor.length === 8) {
                    try {
                        cepInput.classList.add("border-rose-500", "animate-pulse");
                        const res = await fetch(`https://viacep.com.br/ws/${valor}/json/`);
                        const dados = await res.json();
                        cepInput.classList.remove("border-rose-500", "animate-pulse");

                        if (!dados.erro) {
                            if (dados.bairro && bairroInput) bairroInput.value = dados.bairro;
                            if (dados.logradouro && logradouroInput) logradouroInput.value = dados.logradouro;

                            if (dados.localidade && cidadeSelect) {
                                let match = false;
                                for (let i = 0; i < cidadeSelect.options.length; i++) {
                                    if (cidadeSelect.options[i].value.toLowerCase() === dados.localidade.toLowerCase()) {
                                        cidadeSelect.selectedIndex = i;
                                        match = true;
                                        break;
                                    }
                                }
                                if (!match) {
                                    cidadeSelect.value = "Outra Cidade (SP)";
                                    if (campoOutraCidade) campoOutraCidade.classList.remove("hidden");
                                    if (cidadeOutraInput) {
                                        cidadeOutraInput.value = dados.localidade;
                                        cidadeOutraInput.required = true;
                                    }
                                } else {
                                    if (campoOutraCidade) campoOutraCidade.classList.add("hidden");
                                    if (cidadeOutraInput) cidadeOutraInput.required = false;
                                }
                            }
                        }
                    } catch (err) {
                        console.warn("[ViaCEP] Falha na consulta de CEP:", err);
                        cepInput.classList.remove("border-rose-500", "animate-pulse");
                    }
                }
            });
        }
    });
});
