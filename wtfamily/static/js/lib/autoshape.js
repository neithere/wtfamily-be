(function () {
	
	window.AutoshapeJS = new function () {
		var REGEX, SHAPES, extend, merge, parseConstructorString, dashedToCamel;
		
		/* Constants */
		// Private
		REGEX = {
			SHAPE: new RegExp('shape-[\\S]+'),
			BORDERRADIUS: new RegExp('border-(?:(?:top|bottom)-(?:left|right)-){0,1}radius'),
			CALCULATESIZE: new RegExp('^(\\()?([\\d]+)(.*?)(\\))?$'),
			ISATTACHED: new RegExp('(^|\\s)attached(\\s|$)')
		};
		
		// Public
		this.VERSION = '.1';
		this.AUTHOR = 'Chandler Prall <chandler.prall@gmail.com>';
		
			
		/* Properties */
		SHAPES = {};
		SHAPES.Shape = function () {};
		SHAPES.Shape.prototype.init = function (config) {
			// Load default values
			this.mergeAttributes(config);
			
			this.element = document.createElement('DIV');
			this.setStyle('display', 'inline-block');
			this.setStyle('border-style', 'solid');
			this.setStyle('border-width', '0');
			
			this.render();
		};
		SHAPES.Shape.prototype.attributes = {
			rotate: function (value) { this.setStyle('rotate', value + 'deg'); },
			opacity: 'opacity',
			color: 'color',
			transformorigin: function (value) { this.setStyle('transform-origin', value.replace(/\|/g, ' ')); },
			position: 'position',
			left: function (value) { this.setStyle('left', this.calculateSize(value, '%d')); },
			top: function (value) { this.setStyle('top', this.calculateSize(value, '%d')); }
		};
		SHAPES.Shape.prototype.config = {
			rotate: 0, // Angle of clockwise rotation, in degrees
			opacity: 1, // Shape opacity, 0.0 - 1.0
			color: 'black',
			transformorigin: '50% 50%', // Origin of CSS transform,
			position: 'relative',
			left: 'auto',
			top: 'top'
		};
		SHAPES.Shape.prototype.mergeAttributes = function (config) {
			this.attributes = merge(this._extended.attributes, this.attributes);
			this.config = merge(this._extended.config, this.config, (typeof config === 'object' ? config : {}));
		};
		SHAPES.Shape.prototype.setStyle = function (attribute, value) {
			
			var element = this.element;
			
			// Border Radius
			if (REGEX.BORDERRADIUS.test(attribute)) {
				attribute = dashedToCamel(attribute);
				element.style['Moz' + attribute.charAt(0).toUpperCase() + attribute.slice(1)] = value;
				element.style['Webkit' + attribute.charAt(0).toUpperCase() + attribute.slice(1)] = value;
				element.style[attribute] = value;
				return true;
			}
			
			// Rotation
			if (attribute === 'rotate') {
				element.style.MozTransform = element.style.WebkitTransform = element.style.OTransform = element.style.msTransform = element.style.transform = 'rotate(' + value + ')';
				return true;
			}
			
			// Transform Origin
			if (attribute === 'transform-origin') {
				element.style.MozTransformOrigin = element.style.WebkitTransformOrigin = element.style.OTransformOrigin = element.style.msTransformOrigin = element.style.transformOrigin = value;
				return true;
			}
			
			element.style[dashedToCamel(attribute)] = value;
			
			return true;
		};
		SHAPES.Shape.prototype.calculateSize = function (value, operation, placeholder) {
			var parts, unit;
			
			if (typeof value === 'undefined' || typeof operation === 'undefined') { return false; }
			
			parts = value.match(REGEX.CALCULATESIZE);
			if (parts === null) { return 0; }
			
			value = parts[2];
			unit = parts[3].length > 0 ? parts[3] : 'px';
			
			if (parts[1] === '(' && parts[4] === ')') {
				value = value * -1;
			}
			
			placeholder = placeholder || '%d';
			
			operation = operation.replace(new RegExp(placeholder, 'g'), value);
			return eval(operation) + unit;
		};
		SHAPES.Shape.prototype.set = function (attribute, value) {
			this.config[attribute] = value;
			this.render();
		};
		SHAPES.Shape.prototype.get = function (attribute) {
			var value;
			if (attribute in this.config) {
				value = this.config[attribute];
			} else {
				value = this.element.style.getAttribute(attribute);
			}
			return value;
		};
		SHAPES.Shape.prototype.render = function () {
			var key, attribute;
			if (typeof this.element === 'undefined') { return false; }
			
			for (key in this.attributes) {
				attribute = this.attributes[key];
				switch (typeof attribute) {
				case 'string':
					this.setStyle(this.attributes[key], this.config[key]);
					break;
				case 'function':
					attribute.call(this, this.config[key]);
					break;
				}
			}
		};
		SHAPES.Shape.prototype.attachTo = function (element) {
			if (typeof element === 'undefined') { return false; }
			if (typeof element === 'string') { element = document.getElementById(element); }
			if (typeof element.appendChild === 'undefined') { return false; }
			element.appendChild(this.element);
		};
		
		
		/* Methods */
		// Private
		var getElementsByClassName = document.getElementsByClassName || function getElementsByClassName(classname) {
			if  (!(classname instanceof RegExp)) { classname = new RegExp('(^|\\W)' + classname + '($|\\W)'); }
			
			var elements = [];
			if (classname.test(this.className)) {
				elements.push(this);
			}
			
			for (var i = 0; i < this.childNodes.length; i++) {
				elements = elements.concat(getElementsByClassName.call(this.childNodes[i], classname));
			}
			
			return elements;
		};
		
		var extend = function (base, extension) {
			var extended, key, value;
			if (typeof base !== 'function' || typeof base.prototype === 'undefined') { return false; } // We can only extend a prototype
			if (typeof extension !== 'object') { return false; } // We can only extend using an object
			
			extended = function () {};
			extended.prototype = new base();
			extended.prototype._extended = base.prototype;
			
			for (key in extension) {
				value = extension[key];
				
				extended.prototype[key] = value;
				
				if (typeof value === 'function' && typeof base.prototype[key] !== 'undefined') {
					
					(function (extended, base, key) {
						extended.prototype[key]._super = function (source_obj) {
							var args = Array.prototype.slice.call(arguments, 1);
							base.prototype[key].apply(source_obj, args);
						};
					}(extended, base, key));
				}
			}
			
			return extended;
		};
		
		var merge = function () {
			var i, obj, key, merged = {};
			
			for (i = 0; i < arguments.length; i++) {
				obj = arguments[i];
				if (typeof obj !== 'object') { continue; } // We can only merge objects
				
				for (key in obj) {
					merged[key] = obj[key];
				}
			}
			
			return merged;
		};
		
		var parseConstructorString = function (constructor_string) {
			var config = {}, // config is the return value
				parts = constructor_string.split('-'), // split the constructor string into parts
				shape,
				i,
				part,
				key_value;
			parts.shift(); // pull off the "shape" value
			
			// Build config object
			shape = parts.shift();
			if (typeof shape === 'undefined') { return false; }
			config.shape = shape.substr(0,1).toUpperCase() + shape.substr(1).toLowerCase();
			for (i = 0; i < parts.length; i++) {
				part = parts[i];
				key_value = part.split(':');
				if (key_value.length === 2) {
					config[key_value[0]] = key_value[1];
				}
			}
			
			return config;
		};
		
		var dashedToCamel = function (value) {
			return value.replace(/-(\w)/g, function (all, letter) {
				return letter.toUpperCase();
			});
		};
		
		
		// Public
		this.defineShape = function (name, shape) {
			// Check to see if this shape has already been defined
			if (typeof SHAPES[name] !== 'undefined') { return false; }
			
			var shape_base = (typeof shape.base === 'undefined') ? 'Shape' : shape.base;
			SHAPES[name] = extend(SHAPES[shape_base], shape);
		};
		
		this.createShape = function (config) {
			if (typeof config === 'string') {
				// config is a string, break it out into an object
				config = parseConstructorString(config);
			}
			
			if (typeof config.shape === 'undefined') { return false; }
			if (typeof SHAPES[config.shape] === 'undefined') { return false; }
			
			// Create the shape
			var shape = new SHAPES[config.shape]();
			shape.init(config);
			
			return shape;
		};
		
		this.attach = function () {
			var elements, i, element, shape_constructor, shape;
			//if (typeof document.getElementsByClassName === 'undefined') { return false; } // Relying on W3C standards for now
			
			elements = getElementsByClassName.call(document, 'autoshape');
			for (i = 0; i < elements.length; i++) {
				element = elements[i];
				shape_constructor = element.className.match(REGEX.SHAPE);
				if (shape_constructor && !REGEX.ISATTACHED.test(element.className)) {
					shape = this.createShape(shape_constructor[0]);
					if (typeof shape.attachTo !== 'undefined') {
						shape.attachTo(element);
						element.className += ' attached';
					}
				}
			}
		};
	};
	
	// Box
	AutoshapeJS.defineShape(
		'Box',
		{
			attributes: {
				height: 'height',
				width: 'width',
				color: 'background-color',
				borderwidth: 'border-width',
				bordercolor: 'border-color'
			},
			config: {
				height: '30px',
				width: '50px',
				borderwidth: '0px',
				bordercolor: 'black'
			}
		}
	);
	
	// Circle
	AutoshapeJS.defineShape(
		'Circle',
		{
			attributes: {
				radius: function (value) {
					this.setStyle('height', this.calculateSize(value, '%d * 2'));
					this.setStyle('width', this.calculateSize(value, '%d * 2'));
					this.setStyle('border-radius', this.calculateSize(value, '%d'));
				},
				color: 'background-color',
				borderwidth: 'border-width',
				bordercolor: 'border-color'
			},
			config: {
				radius: '25px',
				borderwidth: '0px',
				bordercolor: 'black'
			}
		}
	);
	
	// Complex
	AutoshapeJS.defineShape(
		'Complex',
		{
			init: function (children_config) {
				var i, shape_config, child;
				arguments.callee._super(this);
				
				this.setStyle('position', 'relative');
				
				this.children = [];
				for (i = 0; i < children_config.length; i++) {
					shape_config = children_config[i];
					child = AutoshapeJS.createShape(shape_config);
					child.attachTo(this.element);
				}
				
				this.render();
			},
			render: function () {
				var i;
				if (!(this.children instanceof Array)) { return false; } // We must have children to render
				for (i = 0; i < this.children.length; i++) {
					this.children[i].render();
				}
				arguments.callee._super(this);
			}
		}
	);
	
	// Eclipse
	AutoshapeJS.defineShape(
		'Eclipse',
		{
			attributes: {
				radius: function (value) {
					this.setStyle('height', this.calculateSize(value, '%d * 2'));
					this.setStyle('width', this.calculateSize(value, '%d * 2'));
					this.setStyle('border-radius', value);
				},
				color: function (value) {value = value.replace(/\|/g, ' '); this.setStyle('border-color', value); },
				width: function (value) {value = value.replace(/\|/g, ' '); this.setStyle('border-width', value); }
			},
			config: {
				radius: '25px',
				width: '1px|0|0|0'
			}
		}
	);
	
	// Polygon
	AutoshapeJS.defineShape(
		'Polygon',
		{
			base: 'Complex',
			init: function (config) {
				var children, blockwidth, i;
				this.mergeAttributes(config);
				
				children = [];
				blockwidth = this.calculateSize(this.config.radius, '2 * %d * Math.tan(Math.PI/' + this.config.sides + ')');
				
				// Create blocks
				for (i = 0; i < this.config.sides; i++) {
					children.push({
						shape: 'Box',
						color: this.config.color,
						height: this.calculateSize(this.config.radius, '%d'),
						width: blockwidth,
						rotate: ((360 / this.config.sides) * i) + 180,
						transformorigin: '50% 100%',
						position: 'absolute',
						left: this.calculateSize(this.config.radius, '%d - (' + parseInt(blockwidth) + ' / 2)'),
						top: '0%'
					});
				}
				
				arguments.callee._super(this, children);
			},
			attributes: {
				radius: function (value) {
					this.setStyle('height', this.calculateSize(value, '%d * 2'));
					this.setStyle('width', this.calculateSize(value, '%d * 2'));
				}
			},
			config: {
				radius: '20px',
				sides: 5
			},
			render: function () {
				arguments.callee._super(this);
				
				this.setStyle('height', this.calculateSize(this.config.radius, '%d * 2'));
				this.setStyle('width', this.calculateSize(this.config.radius, '%d * 2'));
			}
		}
	);
	
	// Star
	AutoshapeJS.defineShape(
		'Star',
		{
			base: 'Complex',
			init: function (config) {
				var children, i;
				this.mergeAttributes(config);
				
				// Create config for our child elements
				children = [];
				
				// Spikes
				for (i = 0; i < this.config.spikes; i++) {
					children.push({
						shape: 'Triangle',
						color: this.config.color,
						height: this.calculateSize(this.config.radius, '%d'),
						width: this.config.spikewidth,
						rotate: (360 / this.config.spikes) * i,
						transformorigin: '50% 100%',
						position: 'absolute',
						left: this.calculateSize(this.config.radius, '%d - (' + parseInt(this.config.spikewidth) + ' / 2)'),
						top: '0'
					});
				}
				
				arguments.callee._super(this, children);
			},
			attributes: {
				radius: function (value) {
					this.setStyle('height', this.calculateSize(value, '%d * 2'));
					this.setStyle('width', this.calculateSize(value, '%d * 2'));
				}
			},
			config: {
				radius: '40px',
				spikes: 5,
				spikewidth: '10px'
			},
			render: function () {
				arguments.callee._super(this);
				
				this.setStyle('height', this.calculateSize(this.config.radius, '%d * 2'));
				this.setStyle('width', this.calculateSize(this.config.radius, '%d * 2'));
			}
		}
	);
	
	// Triangle
	AutoshapeJS.defineShape(
		'Triangle',
		{
			init: function (config) {
				arguments.callee._super(this, config);
				
				this.setStyle('border-color', 'transparent');
				this.setStyle('height', '0');
				this.setStyle('width', '0');
				
				this.render();
			},
			attributes: {
				height: function (value) { this.setStyle('border-bottom-width', this.calculateSize(this.config.height, '%d')) },
				width: function (value) {
					if (this.config.type === 'oblique') {
						this.setStyle('border-left-width', this.calculateSize(this.config.width, '%d / 2'));
						this.setStyle('border-right-width', this.calculateSize(this.config.width, '%d / 2'));
					} else if (this.config.type === 'left') {
						this.setStyle('border-right-width', this.config.width);
					} else if (this.config.type === 'right') {
						this.setStyle('border-left-width', this.config.width);
					}
				},
				color: 'border-bottom-color'
			},
			config: {
				height: '50px',
				width: '50px',
				type: 'oblique'
			}
		}
	);
	
	
	/*
	 * Following codeblock taken and modified from John Resig's
	 * "Secrets of the Javascript Ninja" and is under the MIT license.
	 */
	var isReady = false, DOMContentLoaded;
	
	function ready() {
		if (!isReady) {
			AutoshapeJS.attach();
			isReady = true;
		}
	}
	
	// The DOM ready check for Internet Explorer
	function doScrollCheck() {
		if (isReady) {
			return;
		}
		
		try {
			// If IE is used, use the trick by Diego Perini
			// http://javascript.nwbox.com/IEContentLoaded/
			document.documentElement.doScroll("left");
		} catch(error) {
			setTimeout(doScrollCheck, 1);
			return;
		}
		
		// and execute any waiting functions
		ready();
	}
	
	// Catch cases where addReady is called after the
	// browser event has already occurred.
	if (document.readyState === "complete") {
		return ready();
	}
	
	// Mozilla, Opera and Webkit currently support this event
	if (document.addEventListener) {
		
		DOMContentLoaded = function () {
			document.removeEventListener("DOMContentLoaded", DOMContentLoaded, false);
			ready();
		};
		
		// Use the handy event callback
		document.addEventListener("DOMContentLoaded", DOMContentLoaded, false);
	
	} else if (document.attachEvent) {
		
		// IE event model is used
		DOMContentLoaded = function () {
			if (document.readyState === "complete") {
				document.detachEvent("onreadystatechange", DOMContentLoaded);
				ready();
			}
		};
		
		// ensure firing before onload,
		// maybe late but safe also for iframes
		document.attachEvent("onreadystatechange", DOMContentLoaded);
		
		// If IE and not a frame
		// continually check to see if the document is ready
		var toplevel = false;
		try {
			toplevel = window.frameElement === null;
		} catch (e) {}
		if (document.documentElement.doScroll && toplevel) {
			doScrollCheck();
		}
		
	}
	
})();