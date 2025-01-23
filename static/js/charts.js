let myChart = null;

async function fetchWinrates() {
    const response = await fetch('/get_winrates');
    const data = await response.json();
    return data;
}

async function updateChart() {
    const data = await fetchWinrates();
    const ctx = document.getElementById('winrateChart').getContext('2d');
    
    if (myChart) {
        myChart.destroy();
    }
    
    // 准备图表数据
    const labels = [...new Set(data.map(item => item.class1))];
    const datasets = labels.map(class1 => {
        const classData = data.filter(item => item.class1 === class1);
        return {
            label: class1,
            data: labels.map(class2 => {
                if (class1 === class2) return null;
                const match = classData.find(item => item.class2 === class2);
                return match ? match.winrate : null;
            }),
            fill: false,
            borderColor: getRandomColor(),
            tension: 0.1
        };
    });

    myChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: '胜率 (%)'
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'DuelScope - 职业对战胜率统计'
                }
            }
        }
    });
}

function getRandomColor() {
    const letters = '0123456789ABCDEF';
    let color = '#';
    for (let i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

function showAllData() {
    document.getElementById('date').value = '';
    updateChart();
}

// 页面加载时显示所有数据
window.onload = updateChart; 