// CornerIconOverlay.swift
import SwiftUI

private struct CornerIconModifier: ViewModifier {
    let name: String
    let size: CGFloat
    let alignment: Alignment
    let cornerRadius: CGFloat
    let xPadding: CGFloat
    let yPadding: CGFloat
    let action: (() -> Void)?

    func body(content: Content) -> some View {
        content.overlay(alignment: alignment) {
            let img = Image(name)
                .resizable()
                .aspectRatio(contentMode: .fit)
                .frame(width: size, height: size)
                .clipShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
                .shadow(color: .black.opacity(0.25), radius: 6, x: 0, y: 3)
                .padding(.top, yPadding)
                .padding(.trailing, xPadding)

            if let action { img.onTapGesture { action() } }
            else { img.allowsHitTesting(false).accessibilityHidden(true) }
        }
    }
}

public extension View {
    /// Sobrepõe um ícone no canto da janela.
    /// - Parameters:
    ///   - name: nome do asset (ex.: "cornerIcon")
    ///   - size: tamanho do ícone
    ///   - alignment: canto (padrão .topTrailing)
    ///   - xPadding/yPadding: recuos da borda
    ///   - action: toque opcional (se nil, não intercepta cliques)
    func cornerIcon(
        _ name: String,
        size: CGFloat = 56,
        alignment: Alignment = .topTrailing,
        xPadding: CGFloat = 12,
        yPadding: CGFloat = 10,
        cornerRadius: CGFloat = 12,
        onTap action: (() -> Void)? = nil
    ) -> some View {
        modifier(CornerIconModifier(
            name: name,
            size: size,
            alignment: alignment,
            cornerRadius: cornerRadius,
            xPadding: xPadding,
            yPadding: yPadding,
            action: action
        ))
    }
}
