% Santos Cruz Lair Abraham - 322266395 
% Análisis Numérico - Grupo 5
% Unidad 5, Código 5 - Métodos de Euler, Huen, Punto Medio y Runge-Kutta
% de 4° Orden

clear;close all;clc

% -----------------------------------------------------------------------
% Definimos el problema
% -----------------------------------------------------------------------

y0 = 2; % Condición inicial
h = 0.01; % Paso
t0 = 1; % Tiempo inicial
tf = 2; % Tiempo final
t = t0:h:tf; % Vector de t
n = length(t);
dydt = @(t, y) t^2 * y + 3*t; % EDO
y_real = exp(t.^2) .* exp(-1);


% -----------------------------------------------------------------------
% Método de Euler
% -----------------------------------------------------------------------

% Inicializamos vectores
y_euler = zeros(1, n);
et_euler = zeros(1, n);

% Condición inicial
y_euler(1) = y0;

% Implementación

fprintf("Método de Euler: \n");

for i = 1: n - 1
    % Fórmula
    y_euler(i + 1) = y_euler(i) + h * dydt(t(i), y_euler(i));

    % Error
    et_euler(i + 1) = abs((y_real(i + 1) - y_euler(i + 1))/y_real(i + 1)) * 100;

    % Impresión de resultados
    fprintf("%d. t: %.4f, Solución experimental: %.4f, Solución real: %.4f, Error: %.4f%%\n", i, t(i + 1), y_euler(i + 1), y_real(i + 1), et_euler(i + 1));
end

fprintf("\n");

% -----------------------------------------------------------------------
% Método de Huen
% -----------------------------------------------------------------------

% Inicializamos vectores
y_huen = zeros(1, n);
et_huen = zeros(1, n);

% Condición inicial
y_huen(1) = y0;

% Implementación
fprintf("Método de Huen:\n")

for i = 1: n - 1
    % Ecuación predictora
    y_pred = y_huen(i) + h * dydt(t(i), y_huen(i));

    % Corrector
    y_huen(i + 1) = y_huen(i) + (h/2)*(dydt(t(i), y_huen(i)) + dydt(t(i + 1), y_pred));

    % Error
    et_huen(i + 1) = abs((y_real(i + 1) - y_huen(i + 1))/y_real(i + 1)) * 100;

    % Impresión de resultados
    fprintf("%d. t: %.4f, Solución experimental: %.4f, Solución real: %.4f, Error: %.4f%%\n", i, t(i + 1), y_huen(i + 1), y_real(i + 1), et_huen(i + 1));
end

fprintf("\n");

% -----------------------------------------------------------------------
% Método de Punto Medio
% -----------------------------------------------------------------------

% Inicializamos vectores
y_pm = zeros(1, n);
et_pm = zeros(1, n);

% Condición inicial
y_pm(1) = y0;

% Implementación
fprintf("Método del Punto Medio: \n")

for i = 1: n - 1
    % Puntos medios
    tm = t(i) + h/2; 
    ym = y_pm(i) + (h/2)*(dydt(t(i), y_pm(i)));

    % Aplicación
    y_pm(i + 1) = y_pm(i) + h*dydt(tm, ym);

    % Error
    et_pm(i + 1) = abs((y_real(i + 1) - y_pm(i + 1))/y_real(i + 1)) * 100;

    % Impresión de resultados
    fprintf("%d. t: %.4f, Solución experimental: %.4f, Solución real: %.4f, Error: %.4f%%\n", i, t(i + 1), y_pm(i + 1), y_real(i + 1), et_pm(i + 1));
end

fprintf("\n");

% -----------------------------------------------------------------------
% Método de Runge - Kutta 4° Orden
% -----------------------------------------------------------------------

% Inicializamos vectores
y_rk = zeros(1, n);
et_rk = zeros(1, n);

% Condición inicial
y_rk(1) = y0;

% Implementación

fprintf(" Método de Runge - Kutta de 4° Orden:\n");

for i = 1: n - 1
    % Definimos K
    k1 = dydt(t(i), y_rk(i));
    k2 = dydt(t(i) + h/2, y_rk(i) + h/2 * k1);
    k3 = dydt(t(i) + h/2, y_rk(i) + h/2 * k2);
    k4 = dydt(t(i) + h, y_rk(i) + h * k3);

    % Aplicación
    y_rk(i + 1) = y_rk(i) + (h/6) * (k1 + 2*k2 + 2*k3 + k4);

    % Error
    et_rk(i + 1) = abs((y_real(i + 1) - y_rk(i + 1))/y_real(i + 1)) * 100;

    % Impresión de resultados
    fprintf("%d. t: %.4f, Solución experimental: %.4f, Solución real: %.4f, Error: %.4f%%\n", i, t(i + 1), y_rk(i + 1), y_real(i + 1), et_rk(i + 1));
end

fprintf("\n");

% -----------------------------------------------------------------------
% Gráfica de resultados
% -----------------------------------------------------------------------

figure;
plot(t, y_real, 'k-', 'LineWidth', 2); % Solución real
hold on
plot(t, y_euler, '--o', 'LineWidth', 1.5); % Euler
plot(t, y_huen, '--s', 'LineWidth', 1.5); % Huen
plot(t, y_pm, '--^', 'LineWidth', 1.5); % Punto Medio
plot(t, y_rk, '--pm', 'LineWidth', 1.5); % Runge - Kutta

% Etiquetas y Leyendas
xlabel('t');
ylabel('y');
legend('Solución Exacta (e^{t^2 - 1})', 'Método de Euler', ...
    'Método de Huen', 'Método de Punto Medio', ...
    'Método de Runge - Kutta de 4° Orden', 'Location', 'NorthWest');
grid on;