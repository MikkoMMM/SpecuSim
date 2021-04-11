from panda3d.core import Shader as Panda3dShader

basic_lighting_shader = Panda3dShader.make(Panda3dShader.SL_GLSL,
vertex = '''
#version 140
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;

in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
out vec2 texcoord;

in vec3 p3d_Normal;
out vec3 world_normal;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    texcoord = p3d_MultiTexCoord0;
    world_normal = normalize(mat3(p3d_ModelMatrix) * p3d_Normal);
}
''',

fragment='''
#version 140

uniform sampler2D p3d_Texture0;
uniform vec4 p3d_ColorScale;
in vec2 texcoord;
in vec3 world_normal;
out vec4 fragColor;


void main() {
    vec4 norm = vec4(world_normal*0.5+0.5, 1);
    float grey = 0.21 * norm.r + 0.71 * norm.g + 0.07 * norm.b;
    norm = vec4(grey, grey, grey, 1);
    vec4 color = texture(p3d_Texture0, texcoord) * p3d_ColorScale * norm;
    fragColor = color.rgba;
}


''', geometry='',
)
