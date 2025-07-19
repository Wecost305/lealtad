// Agrega al inicio de node.js
const cors = require('cors');
require('dotenv').config();
const express = require('express');
const { Client } = require('@notionhq/client');
const nodemailer = require('nodemailer');

const app = express();
app.use(cors());
app.use(express.json());

// Configuración Notion
const notion = new Client({ auth: process.env.NOTION_TOKEN });
const CLIENTES_DB_ID = '23482f82b06b806c82eefd37451d017e';
const VISITAS_DB_ID = '23482f82b06b8005b8f6ceb70594775a';

// -------------------------- REGISTRO DE TARJETAS --------------------------
app.post('/register-card', async (req, res) => {
    try {
        const { cardId, nombre, telefono, correo, meta } = req.body;
        
        // Verificar si tarjeta ya existe
        const existing = await notion.databases.query({
            database_id: CLIENTES_DB_ID,
            filter: { 
                property: 'ID Tarjeta', 
                rich_text: { equals: cardId }
            }
        });
        
        if (existing.results.length > 0) {
            return res.status(400).json({
                success: false, 
                error: 'Esta tarjeta ya está registrada' 
            });
        }
        
        // Crear nuevo cliente
        const response = await notion.pages.create({
            parent: { database_id: CLIENTES_DB_ID },
            properties: {
                'Nombre': { 
                    title: [{ 
                        text: { content: nombre } 
                    }] 
                },
                'Teléfono': { 
                    rich_text: [{ 
                        text: { content: telefono } 
                    }] 
                },
                'Correo': { email: correo },
                'ID Tarjeta': { 
                    rich_text: [{ 
                        text: { content: cardId } 
                    }] 
                },
                'Visitas': { number: 0 },
                'Meta': { number: parseInt(meta) },
                'Registro': { date: { start: new Date().toISOString() } }
            }
        });
        
        res.json({ 
            success: true,
            id: response.id
        });
        
    } catch (error) {
        console.error('Error en register-card:', error);
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// -------------------------- REGISTRO DE VISITAS --------------------------
app.post('/register-visit', async (req, res) => {
    try {
        const { cardId } = req.body;
        const now = new Date().toISOString();
        
        // 1. Buscar cliente
        const clientResponse = await notion.databases.query({
            database_id: CLIENTES_DB_ID,
            filter: { 
                property: 'ID Tarjeta', 
                rich_text: { equals: cardId }
            }
        });
        
        if (clientResponse.results.length === 0) {
            return res.status(404).json({ 
                success: false, 
                error: 'Cliente no encontrado' 
            });
        }
        
        const client = clientResponse.results[0];
        const visitasActuales = client.properties.Visitas.number || 0;
        const meta = client.properties.Meta.number || 10;
        
        // 2. Actualizar cliente
        await notion.pages.update({
            page_id: client.id,
            properties: {
                'Visitas': { number: visitasActuales + 1 },
                'Última Visita': { date: { start: now } }
            }
        });
        
        // 3. Crear registro de visita
        const visitaResponse = await notion.pages.create({
            parent: { database_id: VISITAS_DB_ID },
            properties: {
                'Cliente': { relation: [{ id: client.id }] },
                'Fecha': { date: { start: now } },
                'Localizador': { 
                    rich_text: [{ 
                        text: { 
                            content: `VIS-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
                        } 
                    }] 
                },
                'Contador en Visita': { number: visitasActuales + 1 }
            }
        });
        
        // 4. Verificar premio
        if (visitasActuales + 1 >= meta) {
            enviarPremio(client, visitasActuales + 1);
        }
        
        res.json({ 
            success: true,
            visitId: visitaResponse.id
        });
        
    } catch (error) {
        console.error('Error en register-visit:', error);
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// -------------------------- FUNCIÓN ENVÍO PREMIO --------------------------
async function enviarPremio(client, visitas) {
    try {
        const plantilla = `
        <!DOCTYPE html>
        <html>
        <head>
            <title>¡Has ganado un premio!</title>
        </head>
        <body>
            <h1>¡Felicidades ${client.properties.Nombre.title[0].plain_text}!</h1>
            <p>Has alcanzado ${visitas} visitas y ganaste: Cena para dos</p>
            <p>Localizador: {Localizador}</p>
        </body>
        </html>
        `;

        // Obtener último localizador
        const visitasResponse = await notion.databases.query({
            database_id: VISITAS_DB_ID,
            filter: { property: 'Cliente', relation: { contains: client.id } },
            sorts: [{ property: 'Fecha', direction: 'descending' }],
            page_size: 1
        });
        
        let contenido = plantilla;
        if (visitasResponse.results.length > 0) {
            const localizador = visitasResponse.results[0].properties.Localizador.rich_text[0]?.plain_text;
            if (localizador) {
                contenido = contenido.replace('{Localizador}', localizador);
            }
        }

        // CONFIGURACIÓN ACTUALIZADA PARA NETLIFY
        const transporter = nodemailer.createTransport({
            host: 'smtp.gmail.com',
            port: 465,
            secure: true,
            auth: { 
                user: process.env.EMAIL_USER, 
                pass: process.env.EMAIL_PASS 
            }
        });
        
        await transporter.sendMail({
            from: 'fidelidad@tunegocio.com',
            to: client.properties.Correo.email,
            subject: '¡Has ganado un premio!',
            html: contenido
        });
        
        // Resetear contador
        await notion.pages.update({
            page_id: client.id,
            properties: { 'Visitas': { number: 0 } }
        });
        
    } catch (error) {
        console.error('Error enviando premio:', error);
    }
}

// -------------------------- INICIAR SERVIDOR --------------------------
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Servidor corriendo en puerto ${PORT}`);
});