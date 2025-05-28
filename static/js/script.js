// static/js/script.js

document.addEventListener('DOMContentLoaded', () => {
    // Cores para os gráficos (consistente com CSS)
    const plotColors = {
        backgroundPrimary: '#161A27',
        backgroundSecondary: '#1E2233',
        plotBackground: 'rgba(0,0,0,0)',
        textPrimary: '#EAEAEA',
        textSecondary: '#A0A0B5',
        accentPrimary: '#9D4EDD',
        accentSecondary: '#5A189A',
        accentTertiary: '#C77DFF',
        highlightPink: '#F72585',
        gridLines: '#3A3F58',
        colorSequence: ['#9D4EDD', '#C77DFF', '#F72585', '#00BFFF', '#32CD32', '#FFD700']
    };

    const commonChartLayout = {
        font: { family: 'Inter, Arial, sans-serif', color: plotColors.textPrimary, size: 11 },
        paper_bgcolor: plotColors.plotBackground,
        plot_bgcolor: plotColors.plotBackground,
        xaxis: {
            gridcolor: plotColors.gridLines, linecolor: plotColors.gridLines, zeroline: false,
            titlefont: { color: plotColors.textSecondary, size: 12 }, tickfont: { color: plotColors.textSecondary, size: 10 },
            showspikes: true, spikemode: 'across', spikesnap: 'cursor', spikethickness: 1, spikedash: 'dot', spikecolor: plotColors.accentSecondary
        },
        yaxis: {
            gridcolor: plotColors.gridLines, linecolor: plotColors.gridLines, zeroline: false,
            titlefont: { color: plotColors.textSecondary, size: 12 }, tickfont: { color: plotColors.textSecondary, size: 10 },
            showspikes: true, spikemode: 'across', spikesnap: 'cursor', spikethickness: 1, spikedash: 'dot', spikecolor: plotColors.accentSecondary
        },
        legend: {
            font: { color: plotColors.textSecondary, size: 10 }, bgcolor: 'rgba(0,0,0,0)',
            orientation: "h", yanchor: "bottom", y: 1.01, xanchor: "center", x: 0.5
        },
        margin: { l: 60, r: 25, b: 50, t: 70, pad: 5 },
        transition: { duration: 500, easing: 'cubic-in-out' },
        hovermode: 'x unified', // 'closest' pode ser melhor para barras
        dragmode: 'zoom'
    };

    const comparisonChartLayout = { // Layout base para barras e rosca na comparação
        font: { family: 'Inter, Arial, sans-serif', color: plotColors.textPrimary, size: 11 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        legend: { font: { color: plotColors.textSecondary, size: 10 }, bgcolor: 'rgba(0,0,0,0)'},
        margin: { t: 60, b: 40, l: 40, r: 20, pad: 2 }, // Ajustado para gráficos menores
        transition: { duration: 500, easing: 'cubic-in-out' }
    };


    const paisesDropdown = document.getElementById('dropdown-paises');
    const minAnoInput = document.getElementById('min-ano-input');
    const maxAnoInput = document.getElementById('max-ano-input');
    const aplicarFiltrosBtn = document.getElementById('btn-aplicar-filtros');
    const sliderAnosValorSpan = document.getElementById('slider-anos-valor');
    const estatisticasPlaceholder = document.getElementById('tabela-estatisticas-placeholder');
    const dadosDetalhadosPlaceholder = document.getElementById('tabela-dados-detalhados-placeholder');
    const indicadorDropdown = document.getElementById('dropdown-indicador-adicional');
    const graficoIndicadorAdicionalDiv = document.getElementById('grafico-indicador-adicional');


    async function fetchAndPopulate(url, dropdownElement, selectMultiple = false, defaultCount = 0, isIndicador = false) {
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            dropdownElement.innerHTML = '';

            if (isIndicador && data.length > 0) {
                const noneOption = document.createElement('option');
                noneOption.value = ""; noneOption.textContent = "Nenhum";
                dropdownElement.appendChild(noneOption);
            }
            data.forEach((item, index) => {
                const option = document.createElement('option');
                option.value = item; option.textContent = String(item).replace(/_/g, " ");
                dropdownElement.appendChild(option);
            });

            if (selectMultiple && defaultCount > 0) {
                for(let i=0; i < defaultCount && i < dropdownElement.options.length; i++) {
                    dropdownElement.options[i].selected = true;
                }
            } else if (!selectMultiple && data.length > 0) {
                const firstRealOptionIndex = isIndicador ? 1 : 0;
                if (dropdownElement.options.length > firstRealOptionIndex) {
                     dropdownElement.value = dropdownElement.options[firstRealOptionIndex].value;
                } else if (dropdownElement.options.length > 0 && !isIndicador) {
                     dropdownElement.value = dropdownElement.options[0].value;
                }
            }
        } catch (error) { console.error(`Erro ao buscar dados de ${url}:`, error); }
    }

    async function initializeFilters() {
        await fetchAndPopulate('/api/paises', paisesDropdown, true, 2);
        await fetchAndPopulate('/api/lista_indicadores', indicadorDropdown, false, 0, true);
        try {
            const response = await fetch('/api/anos_range');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const range = await response.json();
            minAnoInput.value = range.min_ano; minAnoInput.min = range.min_ano; minAnoInput.max = range.max_ano;
            maxAnoInput.value = range.max_ano; maxAnoInput.min = range.min_ano; maxAnoInput.max = range.max_ano;
            updateAnosValorDisplay();
        } catch (error) { console.error('Erro ao buscar range de anos:', error); }

        fetchDataAndRenderAllCharts();
    }

    function updateAnosValorDisplay() {
        if (sliderAnosValorSpan && minAnoInput.value && maxAnoInput.value) {
            sliderAnosValorSpan.textContent = `${minAnoInput.value} - ${maxAnoInput.value}`;
        }
    }

    function displayLoading(elementId) { /* ... (código existente) ... */
        const el = document.getElementById(elementId);
        if (el) el.innerHTML = `<p class="loading-text" style="text-align:center; color:var(--text-secondary); padding: 20px 0;">Carregando...</p>`;
    }
    function displayEmpty(elementId, message = "Nenhum dado para os filtros selecionados.") { /* ... (código existente) ... */
        const el = document.getElementById(elementId);
        if (el) el.innerHTML = `<p class="empty-text" style="text-align:center; color:var(--text-secondary); padding: 20px 0;">${message}</p>`;
    }

    async function fetchDataAndRenderAllCharts() {
        const selectedPaisesArray = Array.from(paisesDropdown.selectedOptions).map(opt => opt.value);
        const minAnoVal = minAnoInput.value;
        const maxAnoVal = maxAnoInput.value;
        const selectedIndicador = indicadorDropdown.value;

        ['grafico-pib-per-capita-tempo', 'grafico-comparacao-pib-histograma', 'grafico-comparacao-pib-rosca'].forEach(displayLoading);
        displayLoading('tabela-estatisticas-placeholder');
        displayLoading('tabela-dados-detalhados-placeholder');
        if (selectedIndicador) { displayLoading('grafico-indicador-adicional');}
        else { displayEmpty('grafico-indicador-adicional', 'Selecione um indicador para visualizar.');}

        const queryParams = new URLSearchParams({
            paises: selectedPaisesArray.join(','), minAno: minAnoVal, maxAno: maxAnoVal
        });

        try {
            const fullDataResponse = await fetch(`/api/dados_filtrados_completos?${queryParams.toString()}`);
            if (!fullDataResponse.ok) throw new Error(`Full Data HTTP error! status: ${fullDataResponse.status}`);
            const fullFilteredData = await fullDataResponse.json();

            const statsResponse = await fetch(`/api/estatisticas_pib?${queryParams.toString()}`);
            if (!statsResponse.ok) throw new Error(`Stats Data HTTP error! status: ${statsResponse.status}`);
            const statsData = await statsResponse.json();

            updateAnosValorDisplay();

            if (!fullFilteredData || fullFilteredData.length === 0) {
                const emptyLayout = { ...commonChartLayout, title: {text: 'Nenhum dado para os filtros selecionados', font: {color: plotColors.textSecondary, size:14}} };
                Plotly.newPlot('grafico-pib-per-capita-tempo', [], emptyLayout, {responsive: true});
                Plotly.newPlot('grafico-comparacao-pib-histograma', [], {...commonChartLayout, title: {text:'Nenhum dado', font: {color: plotColors.textSecondary, size:14}}}, {responsive: true});
                Plotly.newPlot('grafico-comparacao-pib-rosca', [], {...comparisonChartLayout, title: {text:'Nenhum dado', font: {color: plotColors.textSecondary, size:14}}}, {responsive: true});
                displayEmpty('tabela-dados-detalhados-placeholder');
                renderEstatisticasTable([]); // Limpa tabela de estatísticas
                if (!selectedIndicador) displayEmpty('grafico-indicador-adicional', 'Selecione um indicador.');
                return;
            }
            renderLineChart(fullFilteredData, minAnoVal, maxAnoVal);
            renderComparisonCharts(fullFilteredData, maxAnoVal);
            renderDadosDetalhadosTable(fullFilteredData);
            if (selectedIndicador) {
                renderIndicadorAdicionalChart(fullFilteredData, selectedIndicador, minAnoVal, maxAnoVal);
            } else {
                 displayEmpty('grafico-indicador-adicional', 'Selecione um indicador para visualizar.');
            }
            renderEstatisticasTable(statsData);

        } catch (error) { console.error('Erro ao buscar ou renderizar dados:', error); /* ... (tratamento de erro) ... */ }
    }

    function renderLineChart(data, minAno, maxAno) { /* ... (código existente, sem alterações significativas, apenas garantir uso de commonChartLayout) ... */
        const traces = [];
        const paises = [...new Set(data.map(d => d.Pais))];
        paises.forEach((pais, index) => {
            const dadosPais = data.filter(d => d.Pais === pais).sort((a, b) => a.Ano - b.Ano);
            traces.push({
                x: dadosPais.map(d => d.Ano), y: dadosPais.map(d => d.PIB_per_Capita),
                mode: 'lines+markers', name: pais,
                line: { shape: 'spline', width: 2.5, color: plotColors.colorSequence[index % plotColors.colorSequence.length] },
                marker: { size: 7, symbol: 'circle', line: {width: 1.5, color: plotColors.backgroundSecondary} },
                hovertemplate: `<b>${pais}</b><br>Ano: %{x}<br>PIB per Capita: %{y:,.0f} US$<extra></extra>`
            });
        });
        const layout = {
            ...commonChartLayout,
            title: { text: `Evolução do PIB per Capita (${minAno}-${maxAno})`, font: {size: 15, color: plotColors.textPrimary}, x: 0.5, xanchor: 'center'},
            xaxis: { ...commonChartLayout.xaxis, title: 'Ano' },
            yaxis: { ...commonChartLayout.yaxis, title: 'PIB per Capita (US$)' }
        };
        Plotly.newPlot('grafico-pib-per-capita-tempo', traces, layout, {responsive: true});
    }

    function renderComparisonCharts(fullFilteredData, fallbackAnoTitulo) {
        const paisesNoFiltro = [...new Set(fullFilteredData.map(d => d.Pais))];
        const ultimoAnoData = [];
         paisesNoFiltro.forEach(pais => {
            const dadosPais = fullFilteredData.filter(d => d.Pais === pais);
            if (dadosPais.length > 0) {
                const ultimoRegistro = dadosPais.reduce((ult, atual) => atual.Ano > ult.Ano ? atual : ult, dadosPais[0]);
                ultimoAnoData.push(ultimoRegistro);
            }
        });

        let anoTituloComp = fallbackAnoTitulo;
        if (ultimoAnoData.length > 0) {
            const anosUnicos = [...new Set(ultimoAnoData.map(d => d.Ano))];
            if (anosUnicos.length === 1) anoTituloComp = anosUnicos[0];
            else if (anosUnicos.length > 1) anoTituloComp = `${Math.min(...anosUnicos)}-${Math.max(...anosUnicos)}`;
        }

        // 1. Gráfico de Barras Horizontais Ordenado (substituindo o histograma/pizza anterior)
        if (ultimoAnoData.length > 0) {
            const sortedData = [...ultimoAnoData].sort((a, b) => b.PIB_per_Capita - a.PIB_per_Capita); // Ordena decrescente

            const barData = [{
                y: sortedData.map(d => d.Pais), // Países no eixo Y
                x: sortedData.map(d => d.PIB_per_Capita), // PIB no eixo X
                type: 'bar',
                orientation: 'h', // Barras horizontais
                marker: {
                    color: sortedData.map((_, i) => plotColors.colorSequence[i % plotColors.colorSequence.length]),
                    line: { color: plotColors.backgroundPrimary, width: 1 }
                },
                text: sortedData.map(d => `${(d.PIB_per_Capita / 1000).toFixed(1)}k`), // Texto na barra (ex: 8.9k)
                textposition: 'inside', // Posição do texto
                insidetextanchor: 'middle', // Alinhamento do texto dentro da barra
                textfont: { color: plotColors.backgroundSecondary, size: 10, weight: 'bold' }, // Cor do texto contrastante
                hovertemplate: '<b>%{y}</b><br>PIB per Capita: %{x:,.0f} US$<extra></extra>'
            }];
            const barLayout = {
                ...comparisonChartLayout, // Usar um layout base para comparação
                title: {text: `PIB per Capita Comparativo (${anoTituloComp})`, font: {size: 14, color: plotColors.textPrimary}, x:0.5, xanchor:'center'},
                xaxis: { ...commonChartLayout.xaxis, title: 'PIB per Capita (US$)'},
                yaxis: { ...commonChartLayout.yaxis, autorange: "reversed", tickfont: {size:10}}, // Inverte para maior no topo
                showlegend: false,
                margin: { ...comparisonChartLayout.margin, l: 100 } // Aumentar margem esquerda para nomes de países
            };
            Plotly.newPlot('grafico-comparacao-pib-histograma', barData, barLayout, {responsive: true}); // Usando o div do histograma

            // 2. Gráfico de Rosca (Participação Percentual)
            const totalPIBGrupo = ultimoAnoData.reduce((sum, d) => sum + (d.PIB_per_Capita || 0), 0);
            const donutData = [{
                values: ultimoAnoData.map(d => d.PIB_per_Capita),
                labels: ultimoAnoData.map(d => d.Pais),
                type: 'pie', hole: 0.5,
                textinfo: 'percent', // Mostrar apenas percentual
                textfont: { size: 11, color: 'white' },
                textposition: 'inside',
                marker: { colors: plotColors.colorSequence, line: { color: plotColors.backgroundPrimary, width: 2.5 } },
                hovertemplate: '<b>%{label}</b><br>PIB: %{value:,.0f} US$<br>Participação: %{percent}<extra></extra>',
                sort: false
            }];
            const donutLayout = {
                ...comparisonChartLayout,
                title: {text: `Participação no PIB do Grupo (${anoTituloComp})`, font: {size: 14, color: plotColors.textPrimary}, x:0.5, xanchor:'center'},
                showlegend: true,
                legend: {...commonChartLayout.legend, orientation:'v', x:1.05, xanchor:'left', y:0.5, yanchor:'middle', font: {size:9}}
            };
            Plotly.newPlot('grafico-comparacao-pib-rosca', donutData, donutLayout, {responsive: true});

        } else {
            const emptyCompLayout = {...comparisonChartLayout, title: {text:'Nenhum dado', font: {color: plotColors.textSecondary, size:14}}};
            Plotly.newPlot('grafico-comparacao-pib-histograma', [], emptyCompLayout, {responsive: true});
            Plotly.newPlot('grafico-comparacao-pib-rosca', [], emptyCompLayout, {responsive: true});
        }
    }

    function renderEstatisticasTable(statsData) { /* ... (código existente) ... */
        const container = document.getElementById('tabela-estatisticas-placeholder');
        if (!statsData || statsData.length === 0) {
            container.innerHTML = '<p class="empty-text">Nenhuma estatística disponível.</p>'; return;
        }
        let tableHTML = '<table class="stats-table">';
        tableHTML += `<thead><tr><th>País</th><th>Média</th><th>Mediana</th><th>Desv. Padrão</th><th>Mín.</th><th>Máx.</th><th>Variação</th></tr></thead><tbody>`;
        statsData.forEach(stat => {
            tableHTML += `<tr>
                    <td>${stat.País || 'N/A'}</td>
                    <td>${stat.Média !== undefined ? stat.Média.toLocaleString() : 'N/A'}</td>
                    <td>${stat.Mediana !== undefined ? stat.Mediana.toLocaleString() : 'N/A'}</td>
                    <td>${stat['Desvio Padrão'] !== undefined ? stat['Desvio Padrão'].toLocaleString() : 'N/A'}</td>
                    <td>${stat.Mínimo !== undefined ? stat.Mínimo.toLocaleString() : 'N/A'}</td>
                    <td>${stat.Máximo !== undefined ? stat.Máximo.toLocaleString() : 'N/A'}</td>
                    <td>${stat['Variação no Período'] !== undefined ? stat['Variação no Período'].toLocaleString() : 'N/A'}</td>
                </tr>`;
        });
        tableHTML += '</tbody></table>';
        container.innerHTML = tableHTML;
    }

    function renderDadosDetalhadosTable(fullFilteredData) {
        const container = document.getElementById('tabela-dados-detalhados-placeholder');
        if (!fullFilteredData || fullFilteredData.length === 0) {
            container.innerHTML = '<p class="empty-text">Nenhum dado detalhado para os filtros.</p>'; return;
        }
        // Definir colunas explicitamente para ordem e formatação
        const colunasVisiveis = ['Pais', 'Ano', 'PIB_per_Capita', 'Continent', 'Type', 'CAGR_Forecast'];
        // Adicionar outras colunas do seu CSV que sejam relevantes:
        // Ex: 'Population', 'GDP_Growth_Rate' (se existirem no fullFilteredData[0])
        const headersExistentes = fullFilteredData.length > 0 ? Object.keys(fullFilteredData[0]) : [];
        const headers = colunasVisiveis.filter(col => headersExistentes.includes(col));

        let tableHTML = '<div class="table-wrapper"><table class="details-table">';
        tableHTML += '<thead><tr>';
        headers.forEach(header => { tableHTML += `<th>${header.replace(/_/g, " ")}</th>`; });
        tableHTML += '</tr></thead><tbody>';

        fullFilteredData.forEach(row => {
            tableHTML += '<tr>';
            headers.forEach(header => {
                let cellValue = row[header];
                if (typeof cellValue === 'number') {
                    if (header === 'PIB_per_Capita') cellValue = cellValue.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0});
                    else if (header === 'CAGR_Forecast' || (String(header).toLowerCase().includes('rate') && cellValue < 1 && cellValue > -1)) cellValue = (cellValue * 100).toFixed(2) + '%'; // Formata taxas como %
                    else if (!Number.isInteger(cellValue)) cellValue = cellValue.toFixed(2);
                    else cellValue = cellValue.toLocaleString();
                }
                tableHTML += `<td>${cellValue !== undefined && cellValue !== null && cellValue !== 'N/A' ? cellValue : 'N/A'}</td>`;
            });
            tableHTML += '</tr>';
        });
        tableHTML += '</tbody></table></div>';
        container.innerHTML = tableHTML;
    }

    function renderIndicadorAdicionalChart(data, indicador, minAno, maxAno) {
        const graficoDiv = document.getElementById('grafico-indicador-adicional');
        if (!indicador || indicador === "") {
            graficoDiv.innerHTML = `<p class="empty-text">Selecione um indicador.</p>`; return;
        }
        if (data.length === 0 || !data[0].hasOwnProperty(indicador)) {
            graficoDiv.innerHTML = `<p class="empty-text">Indicador '${indicador.replace(/_/g, " ")}' não encontrado ou sem dados.</p>`; return;
        }

        const traces = [];
        const paises = [...new Set(data.map(d => d.Pais))];
        let dadosParaIndicadorExistem = false;

        paises.forEach((pais, index) => {
            const dadosPais = data.filter(d => d.Pais === pais && d[indicador] !== null && d[indicador] !== undefined && d[indicador] !== 'N/A' && !isNaN(parseFloat(d[indicador])))
                                 .map(d => ({ ...d, [indicador]: parseFloat(d[indicador]) })) // Garante que é número
                                 .sort((a, b) => a.Ano - b.Ano);
            if (dadosPais.length > 0) {
                dadosParaIndicadorExistem = true;
                traces.push({
                    x: dadosPais.map(d => d.Ano), y: dadosPais.map(d => d[indicador]),
                    mode: 'lines+markers', name: pais,
                    line: { shape: 'spline', width: 2.5, color: plotColors.colorSequence[index % plotColors.colorSequence.length] },
                    marker: { size: 7, symbol: 'circle', line: {width: 1.5, color: plotColors.backgroundSecondary} },
                    hovertemplate: `<b>${pais}</b><br>Ano: %{x}<br>${indicador.replace(/_/g, " ")}: %{y:,.2f}<extra></extra>`
                });
            }
        });

        if (!dadosParaIndicadorExistem) {
            graficoDiv.innerHTML = `<p class="empty-text">Não há dados para '${indicador.replace(/_/g, " ")}' com os filtros.</p>`; return;
        }
        const layout = {
            ...commonChartLayout,
            title: { text: `${indicador.replace(/_/g, " ")} (${minAno}-${maxAno})`, font: {size: 15, color: plotColors.textPrimary}, x: 0.5, xanchor: 'center'},
            xaxis: { ...commonChartLayout.xaxis, title: 'Ano' },
            yaxis: { ...commonChartLayout.yaxis, title: indicador.replace(/_/g, " ") }
        };
        Plotly.newPlot('grafico-indicador-adicional', traces, layout, {responsive: true});
    }

    aplicarFiltrosBtn.addEventListener('click', fetchDataAndRenderAllCharts);
    minAnoInput.addEventListener('change', updateAnosValorDisplay);
    maxAnoInput.addEventListener('change', updateAnosValorDisplay);
    indicadorDropdown.addEventListener('change', fetchDataAndRenderAllCharts);

    initializeFilters();
});
