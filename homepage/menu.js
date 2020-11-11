function selectButton(event) {
  const button = event.currentTarget;

  // Remover todas as classes .active
  const buttons = document.querySelectorAll(".menu-button");
  buttons.forEach((button) => {
    button.classList.remove("active");
  });

  // Adicionanr a classe .active para o botão clicado
  button.classList.add("active");
}