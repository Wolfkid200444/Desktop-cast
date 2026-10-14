// Shared output-coordinate calculations. All positions are logical Wayland pixels.
function originFor(screens, name) {
    return screens.find(screen => screen.name === name) || screens[0] || {name: "", x: 0, y: 0};
}

function placement(character, screens, output, drag) {
    const origin = originFor(screens, character.screen);
    const globalX = drag && drag.id === character.id ? drag.x : origin.x + character.x;
    const globalY = drag && drag.id === character.id ? drag.y : origin.y + character.y;
    return {x: globalX - output.x, y: globalY - output.y};
}

function finishMove(character, screens, output, x, y, pointerX, pointerY) {
    const globalX = output.x + x;
    const globalY = output.y + y;
    const destination = screens.find(screen =>
        pointerX >= screen.x && pointerX < screen.x + screen.width &&
        pointerY >= screen.y && pointerY < screen.y + screen.height
    ) || originFor(screens, character.screen);
    return {screen: destination.name, x: Math.round(globalX - destination.x),
            y: Math.round(globalY - destination.y)};
}
