moment.locale("ru");

document.addEventListener("DOMContentLoaded", function () {
  const typeButtons = document.querySelectorAll('input[name="type"]');
  const rangeButtons = document.querySelectorAll('input[name="range"]');
  let selectedType = null;
  let selectedRange = null;

  const ctx = document.getElementById("myChart");
  let myChart = new Chart(ctx, {
    type: "line",
    data: {
      datasets: [
        {
          data: [],
          tension: 0.5,
        },
      ],
    },
    options: {
      plugins: {
        legend: {
          display: false,
        },
      },
      scales: {
        x: {
          type: "time",
          time: {
            unit: "day",
            tooltipFormat: "DD MMMM yyyy г.",
          },
          title: {
            display: true,
            text: "Дата",
          },
        },
        y: {
          title: {
            display: true,
            text: "Значение",
          },
        },
      },
    },
  });

  function updateChart(dataset) {
    myChart.data.datasets[0].data = dataset.data;
    myChart.options.scales.y.title.text = dataset.title;
    myChart.update();
  }

  function fetchData(type, range) {
    const url = `/chart/${type}/${range}`;
    fetch(url)
      .then((response) => response.json())
      .then((data) => {
        updateChart(data);
      })
      .catch((error) => console.error("Ошибка при получении данных:", error));
  }

  function handleChange() {
    if (selectedType && selectedRange) {
      fetchData(selectedType, selectedRange);
    }
  }

  typeButtons.forEach((button) => {
    button.addEventListener("change", function () {
      selectedType = this.id.replace("Button", "").toLowerCase();
      handleChange();
    });
  });

  rangeButtons.forEach((button) => {
    button.addEventListener("change", function () {
      selectedRange = this.id.replace("Button", "").toLowerCase();
      handleChange();
    });
  });

  typeButtons[0].checked = true;
  selectedType = typeButtons[0].id.replace("Button", "").toLowerCase();
  rangeButtons[0].checked = true;
  selectedRange = rangeButtons[0].id.replace("Button", "").toLowerCase();

  handleChange();
});
