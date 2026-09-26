# Local fixture

`sample-cube.glb` is a self-authored cube with 24 vertices, 12 triangles, normals,
and a teal PBR material. It has no textures, external resources, or network
dependencies. Every Phase 1 fake generation returns this same model, regardless
of the uploaded image; it is not an AI reconstruction of that image.

Regenerate it from the repository root:

```sh
python3 fixtures/create_sample.py
```

The fixture and its generation script are dedicated to the public domain under
[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). No third-party model
or image data was used. This single cube verifies the Phase 1 loading flow only;
it does not yet cover the complex editing fixtures planned for Phase 3.
